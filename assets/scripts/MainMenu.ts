import {
    _decorator,
    Button,
    Color,
    Component,
    director,
    EditBox,
    EventTouch,
    game,
    Graphics,
    input,
    Input,
    KeyCode,
    Label,
    Layers,
    Node,
    profiler,
    resources,
    Sprite,
    SpriteFrame,
    sys,
    tween,
    UITransform,
    UIOpacity,
    Vec3,
    Widget,
} from 'cc';
import {
    LLM_PROVIDER_OPTIONS,
    LLM_QUALITY_OPTIONS,
    PlayerLlmSettings,
    loadLlmSettings,
    saveLlmSettings,
} from './LlmSettings';
import { checkLlmBackend, generateLlmText } from './LlmClient';

const { ccclass, property } = _decorator;

type MenuAction = 'start' | 'continue' | 'tests' | 'settings' | 'exit';

interface MenuButtonTheme {
    fill: Color;
    stroke: Color;
    text: Color;
    accent: Color;
}

@ccclass('MainMenu')
export class MainMenu extends Component {
    @property
    public gameSceneName = 'test';

    @property
    public saveKey = 'aitown-save';

    private menuRoot: Node | null = null;
    private settingsPanel: Node | null = null;
    private testsPanel: Node | null = null;
    private llmChatPanel: Node | null = null;
    private statusLabel: Label | null = null;
    private llmProviderValueLabel: Label | null = null;
    private llmQualityValueLabel: Label | null = null;
    private chatInput: EditBox | null = null;
    private chatLogRoot: Node | null = null;
    private backendStatusLabel: Label | null = null;
    private chatMessages: Array<{ role: 'user' | 'assistant'; text: string }> = [];
    private isSendingLlmMessage = false;
    private mainMenuItems: Array<{ node: Node; label: Label }> = [];
    private activeMainMenuIndex = 0;
    private llmSettings: PlayerLlmSettings = loadLlmSettings();

    private readonly normalButton: MenuButtonTheme = {
        fill: new Color(30, 33, 36, 255),
        stroke: new Color(82, 88, 92, 255),
        text: new Color(236, 238, 240, 255),
        accent: new Color(236, 238, 240, 255),
    };

    private readonly activeButton: MenuButtonTheme = {
        fill: new Color(44, 48, 52, 255),
        stroke: new Color(214, 218, 220, 255),
        text: new Color(255, 255, 255, 255),
        accent: new Color(255, 255, 255, 255),
    };

    start() {
        this.node.layer = Layers.Enum.UI_2D;
        (profiler as unknown as { hideStats?: () => void }).hideStats?.();
        this.ensureFullScreen(this.node);
        this.node.getChildByName('MainMenuRoot')?.destroy();

        this.menuRoot = new Node('MainMenuRoot');
        this.menuRoot.layer = Layers.Enum.UI_2D;
        this.menuRoot.setParent(this.node);
        this.ensureFullScreen(this.menuRoot);

        this.buildMenu();
        input.on(Input.EventType.KEY_DOWN, this.onKeyDown, this);
    }

    onDestroy() {
        input.off(Input.EventType.KEY_DOWN, this.onKeyDown, this);
    }

    private buildMenu() {
        if (!this.menuRoot) {
            return;
        }

        this.createBackground();
        this.createBrandBlock();
        this.createMenuPanel();
    }

    private createBackground() {
        const bg = this.createGraphicsNode('Background', this.menuRoot);
        this.ensureFullScreen(bg);

        const g = bg.getComponent(Graphics)!;
        this.fillRect(g, -960, -540, 1920, 1080, new Color(7, 8, 8, 255));

        const image = new Node('BackgroundImage');
        image.layer = Layers.Enum.UI_2D;
        image.setParent(bg);
        this.ensureFullScreen(image);
        const sprite = image.addComponent(Sprite);
        sprite.sizeMode = Sprite.SizeMode.CUSTOM;

        resources.load('main-menu/background/spriteFrame', SpriteFrame, (error, spriteFrame) => {
            if (error || !spriteFrame) {
                console.warn('[MainMenu] failed to load main menu background', error);
                return;
            }
            sprite.spriteFrame = spriteFrame;
        });
    }

    private createBrandBlock() {
        // The imported background already contains the title artwork.
    }

    private createMenuPanel() {
        if (!this.menuRoot) {
            return;
        }

        const panel = new Node('MenuPanel');
        panel.layer = Layers.Enum.UI_2D;
        panel.setParent(this.menuRoot);
        panel.setPosition(-424, -150, 0);
        panel.addComponent(UITransform).setContentSize(230, 250);

        const entries: Array<[string, string, MenuAction]> = [
            ['Start', '建立新的小镇日程', 'start'],
            ['Continue', '读取本地存档状态', 'continue'],
            ['LLM Test', '和当前选择的 AI 聊天', 'tests'],
            ['Settings', '音量、画面和调试选项', 'settings'],
            ['Quit', '关闭当前客户端', 'exit'],
        ];

        this.mainMenuItems = [];
        this.activeMainMenuIndex = 0;

        entries.forEach(([text, detail, action], index) => {
            const button = this.createMainMenuButton(text, action, index);
            button.setParent(panel);
            button.setPosition(0, 54 - index * 36, 0);
        });

        this.setActiveMainMenuIndex(0);

        const statusNode = this.createLabel('', 12, new Color(132, 118, 96, 255), 230);
        statusNode.name = 'Status';
        statusNode.setParent(panel);
        statusNode.setPosition(58, -132, 0);
        statusNode.getComponent(Label)!.horizontalAlign = Label.HorizontalAlign.LEFT;
        this.statusLabel = statusNode.getComponent(Label);
    }

    private createFooter() {
        if (!this.menuRoot) {
            return;
        }

        const footer = this.createLabel('Prototype build 0.1  |  Cocos Creator 3.8.6', 14, new Color(105, 126, 126, 255), 420);
        footer.setParent(this.menuRoot);
        footer.setPosition(-248, -278, 0);
        footer.getComponent(Label)!.horizontalAlign = Label.HorizontalAlign.LEFT;
    }

    private createMainMenuButton(text: string, action: MenuAction, index: number) {
        const node = this.createGraphicsNode(`MainMenu_${action}`);
        node.addComponent(UITransform).setContentSize(220, 34);
        this.drawMainMenuButton(node, false);

        const button = node.addComponent(Button);
        button.transition = Button.Transition.NONE;

        const label = this.createLabel(text, 18, new Color(164, 151, 126, 255), 170);
        label.name = 'Label';
        label.setParent(node);
        label.setPosition(8, 3, 0);
        label.getComponent(Label)!.horizontalAlign = Label.HorizontalAlign.LEFT;
        const labelComponent = label.getComponent(Label)!;
        this.mainMenuItems[index] = { node, label: labelComponent };

        node.on(Node.EventType.MOUSE_ENTER, () => {
            this.setActiveMainMenuIndex(index);
        }, this);

        node.on(Node.EventType.TOUCH_START, () => {
            this.setActiveMainMenuIndex(index);
        }, this);
        node.on(Node.EventType.TOUCH_END, (event: EventTouch) => {
            this.setActiveMainMenuIndex(index);
            this.handleAction(action);
            event.propagationStopped = true;
        }, this);

        return node;
    }

    private setActiveMainMenuIndex(index: number) {
        this.activeMainMenuIndex = index;
        this.mainMenuItems.forEach((item, itemIndex) => {
            const active = itemIndex === this.activeMainMenuIndex;
            this.drawMainMenuButton(item.node, active);
            item.label.color = active ? new Color(242, 226, 198, 255) : new Color(164, 151, 126, 255);
        });
    }

    private drawMainMenuButton(node: Node, active: boolean) {
        const g = node.getComponent(Graphics)!;
        g.clear();
        this.fillRect(g, -80, -15, 170, 1, new Color(76, 66, 52, 190));
        if (!active) {
            return;
        }

        g.fillColor = new Color(205, 76, 49, 255);
        g.moveTo(-78, 2);
        g.lineTo(-68, 8);
        g.lineTo(-78, 14);
        g.close();
        g.fill();
    }

    private createMenuButton(text: string, detail: string, action: MenuAction) {
        const node = this.createGraphicsNode(`Button_${action}`);
        node.addComponent(UIOpacity).opacity = 250;
        node.addComponent(UITransform).setContentSize(260, 42);
        this.drawButton(node, this.normalButton);

        const button = node.addComponent(Button);
        button.transition = Button.Transition.SCALE;
        button.zoomScale = 1.015;
        button.duration = 0.08;

        const label = this.createLabel(text, 17, this.normalButton.text, 220);
        label.name = 'Label';
        label.setParent(node);
        label.setPosition(0, 0, 0);

        node.on(Node.EventType.TOUCH_START, () => this.drawButton(node, this.activeButton), this);
        node.on(Node.EventType.TOUCH_END, (event: EventTouch) => {
            this.drawButton(node, this.normalButton);
            this.handleAction(action);
            event.propagationStopped = true;
        }, this);
        node.on(Node.EventType.TOUCH_CANCEL, () => this.drawButton(node, this.normalButton), this);

        return node;
    }

    private drawButton(node: Node, theme: MenuButtonTheme) {
        const g = node.getComponent(Graphics)!;
        g.clear();
        this.roundRect(g, -130, -21, 260, 42, 5, theme.fill, theme.stroke);
    }

    private toggleSettings() {
        this.closeTestsPanel();
        this.closeLlmChatPanel();
        if (this.settingsPanel?.isValid) {
            this.settingsPanel.destroy();
            this.settingsPanel = null;
            this.setStatus('设置已关闭');
            return;
        }

        const panel = this.createGraphicsNode('SettingsPanel', this.menuRoot);
        panel.setPosition(0, -28, 0);
        panel.addComponent(UITransform).setContentSize(360, 420);
        panel.addComponent(UIOpacity).opacity = 0;

        const g = panel.getComponent(Graphics)!;
        this.roundRect(g, -180, -210, 360, 420, 6, new Color(18, 20, 22, 255), new Color(54, 58, 62, 255));

        const title = this.createLabel('设置', 22, new Color(236, 238, 240, 255), 280);
        title.setParent(panel);
        title.setPosition(0, 164, 0);

        this.llmProviderValueLabel = this.createSettingRow(
            panel,
            'LLM 服务',
            this.getProviderLabel(),
            78,
            () => this.cycleLlmProvider(),
        );
        this.llmQualityValueLabel = this.createSettingRow(
            panel,
            '模型档位',
            this.getQualityLabel(),
            26,
            () => this.cycleLlmQuality(),
        );
        this.createSettingRow(panel, '后端地址', this.llmSettings.serverUrl.replace(/^https?:\/\//, ''), -26);
        this.createSettingRow(panel, '音量', '100%', -78);

        const close = this.createMenuButton('关闭', '返回主菜单', 'settings');
        close.setParent(panel);
        close.setScale(new Vec3(0.82, 0.82, 1));
        close.setPosition(0, -150, 0);

        this.settingsPanel = panel;
        tween(panel.getComponent(UIOpacity)!).to(0.16, { opacity: 255 }).start();
        this.setStatus('设置已打开');
    }

    private toggleTestsPanel() {
        this.closeSettingsPanel();
        this.closeLlmChatPanel();
        if (this.testsPanel?.isValid) {
            this.closeTestsPanel();
            this.setStatus('功能测试已关闭');
            return;
        }

        const panel = this.createGraphicsNode('FunctionTestsPanel', this.menuRoot);
        panel.setPosition(0, -28, 0);
        panel.addComponent(UITransform).setContentSize(360, 420);
        panel.addComponent(UIOpacity).opacity = 0;

        const g = panel.getComponent(Graphics)!;
        this.roundRect(g, -180, -210, 360, 420, 6, new Color(18, 20, 22, 255), new Color(54, 58, 62, 255));

        const title = this.createLabel('功能测试', 22, new Color(236, 238, 240, 255), 280);
        title.setParent(panel);
        title.setPosition(0, 164, 0);

        const llmTest = this.createMenuButton('LLM 测试', '和当前选择的 AI 聊天', 'tests');
        llmTest.setParent(panel);
        llmTest.setPosition(0, 72, 0);
        llmTest.off(Node.EventType.TOUCH_END);
        llmTest.on(Node.EventType.TOUCH_END, (event: EventTouch) => {
            this.drawButton(llmTest, this.normalButton);
            this.openLlmChatPanel();
            event.propagationStopped = true;
        }, this);

        const close = this.createMenuButton('关闭', '返回主菜单', 'tests');
        close.setParent(panel);
        close.setScale(new Vec3(0.82, 0.82, 1));
        close.setPosition(0, -132, 0);

        this.testsPanel = panel;
        tween(panel.getComponent(UIOpacity)!).to(0.16, { opacity: 255 }).start();
        this.setStatus('功能测试已打开');
    }

    private openLlmChatPanel() {
        this.closeTestsPanel();
        this.closeSettingsPanel();
        this.closeLlmChatPanel();

        const panel = this.createGraphicsNode('LlmChatPanel', this.menuRoot);
        panel.setPosition(0, -18, 0);
        panel.addComponent(UITransform).setContentSize(600, 520);
        panel.addComponent(UIOpacity).opacity = 0;

        const g = panel.getComponent(Graphics)!;
        this.roundRect(g, -300, -260, 600, 520, 6, new Color(18, 20, 22, 255), new Color(54, 58, 62, 255));
        this.roundRect(g, -266, -88, 532, 270, 5, new Color(22, 24, 26, 255), new Color(54, 58, 62, 255));
        this.roundRect(g, -266, -166, 408, 46, 5, new Color(30, 33, 36, 255), new Color(82, 88, 92, 255));

        const title = this.createLabel('LLM 测试聊天', 22, new Color(236, 238, 240, 255), 360);
        title.setParent(panel);
        title.setPosition(-70, 224, 0);

        const modelInfo = this.createLabel(`${this.getProviderLabel()} / ${this.getQualityLabel()}`, 15, new Color(151, 174, 166, 255), 240);
        modelInfo.setParent(panel);
        modelInfo.setPosition(146, 224, 0);

        const backendStatus = this.createLabel('后端：检测中', 14, new Color(151, 174, 166, 255), 330);
        backendStatus.setParent(panel);
        backendStatus.setPosition(-70, 168, 0);
        backendStatus.getComponent(Label)!.horizontalAlign = Label.HorizontalAlign.LEFT;
        this.backendStatusLabel = backendStatus.getComponent(Label);
        void this.refreshLlmBackendStatus();

        this.chatLogRoot = new Node('ChatLog');
        this.chatLogRoot.layer = Layers.Enum.UI_2D;
        this.chatLogRoot.setParent(panel);
        this.chatLogRoot.setPosition(0, 38, 0);

        const inputNode = new Node('ChatInput');
        inputNode.layer = Layers.Enum.UI_2D;
        inputNode.setParent(panel);
        inputNode.setPosition(-62, -143, 0);
        inputNode.addComponent(UITransform).setContentSize(390, 40);
        const inputText = this.createLabel('', 14, new Color(239, 245, 233, 255), 330);
        inputText.name = 'InputText';
        inputText.setParent(inputNode);
        inputText.setPosition(178, 0, 0);
        inputText.getComponent(Label)!.horizontalAlign = Label.HorizontalAlign.LEFT;
        const placeholderText = this.createLabel('输入消息', 14, new Color(120, 147, 142, 255), 330);
        placeholderText.name = 'PlaceholderText';
        placeholderText.setParent(inputNode);
        placeholderText.setPosition(178, 0, 0);
        placeholderText.getComponent(Label)!.horizontalAlign = Label.HorizontalAlign.LEFT;
        const input = inputNode.addComponent(EditBox);
        input.placeholder = '';
        input.string = '';
        input.maxLength = 500;
        input.returnType = EditBox.KeyboardReturnType.SEND;
        input.inputMode = EditBox.InputMode.ANY;
        const inputStyle = input as unknown as {
            fontSize?: number;
            lineHeight?: number;
            placeholderFontSize?: number;
            fontColor?: Color;
            placeholderFontColor?: Color;
            textLabel?: Label;
            placeholderLabel?: Label;
        };
        inputStyle.fontSize = 14;
        inputStyle.lineHeight = 20;
        inputStyle.placeholderFontSize = 14;
        inputStyle.fontColor = new Color(239, 245, 233, 255);
        inputStyle.placeholderFontColor = new Color(120, 147, 142, 255);
        inputStyle.textLabel = inputText.getComponent(Label)!;
        inputStyle.placeholderLabel = placeholderText.getComponent(Label)!;
        input.node.on('editing-return', () => this.sendLlmChatMessage(), this);
        this.chatInput = input;

        const send = this.createSmallButton('发送', () => this.sendLlmChatMessage());
        send.setParent(panel);
        send.setPosition(204, -143, 0);

        const check = this.createSmallButton('检测', () => void this.refreshLlmBackendStatus());
        check.setParent(panel);
        check.setPosition(208, 168, 0);

        const back = this.createSmallButton('返回', () => this.toggleTestsPanel());
        back.setParent(panel);
        back.setPosition(112, -220, 0);

        const close = this.createSmallButton('关闭', () => this.closeLlmChatPanel());
        close.setParent(panel);
        close.setPosition(208, -220, 0);

        this.llmChatPanel = panel;
        this.renderChatLog();
        tween(panel.getComponent(UIOpacity)!).to(0.16, { opacity: 255 }).start();
        this.setStatus('LLM 测试聊天已打开');
    }

    private async sendLlmChatMessage() {
        if (this.isSendingLlmMessage) {
            this.setStatus('上一条消息还在处理中');
            return;
        }

        const text = this.chatInput?.string.trim() ?? '';
        if (!text) {
            this.setStatus('请输入消息');
            return;
        }

        if (this.chatInput) {
            this.chatInput.string = '';
            const blur = (this.chatInput as unknown as { blur?: () => void }).blur;
            if (blur) {
                blur.call(this.chatInput);
            }
        }
        this.chatMessages.push({ role: 'user', text });
        this.chatMessages.push({ role: 'assistant', text: '思考中...' });
        this.renderChatLog();
        this.setStatus('正在请求 LLM');
        this.isSendingLlmMessage = true;

        try {
            const historyMessages = this.chatMessages
                .filter((message) => message.text !== '思考中...')
                .slice(-8)
                .map((message) => ({
                    role: message.role,
                    content: message.text,
                }));
            const result = await generateLlmText({
                promptId: 'llm_test',
                messages: historyMessages,
            });
            this.chatMessages[this.chatMessages.length - 1] = { role: 'assistant', text: result.text || '(空回复)' };
            this.setStatus(`LLM 回复完成：${result.model}`);
        } catch (error) {
            this.chatMessages[this.chatMessages.length - 1] = {
                role: 'assistant',
                text: `请求失败：${error?.message ?? String(error)}`,
            };
            this.setStatus('LLM 请求失败');
        } finally {
            this.isSendingLlmMessage = false;
        }

        this.renderChatLog();
    }

    private async refreshLlmBackendStatus() {
        if (!this.backendStatusLabel) {
            return;
        }

        this.backendStatusLabel.string = '后端：检测中';
        const ok = await checkLlmBackend();
        if (!this.backendStatusLabel) {
            return;
        }

        this.backendStatusLabel.string = ok ? '后端：已连接' : '后端：未启动，先运行 npm run start:llm';
        this.backendStatusLabel.color = ok ? new Color(132, 211, 151, 255) : new Color(236, 174, 88, 255);
    }

    private renderChatLog() {
        if (!this.chatLogRoot) {
            return;
        }

        this.chatLogRoot.removeAllChildren();
        const fontSize = 15;
        const lineHeight = 22;
        const paddingX = 16;
        const paddingY = 10;
        const gap = 8;
        const chatAreaWidth = 532;
        const chatAreaHeight = 270;
        const maxBubbleWidth = 470;
        const minBubbleWidth = 108;
        const maxTextWidth = maxBubbleWidth - paddingX * 2;
        const leftX = -chatAreaWidth / 2 + 14;
        const rightX = chatAreaWidth / 2 - 14;

        const visible = this.chatMessages.slice(-8).map((message) => {
            const isUser = message.role === 'user';
            const displayText = `${isUser ? '你' : 'AI'}：${this.normalizeChatText(message.text)}`;
            const lines = this.wrapTextToWidth(displayText, maxTextWidth, fontSize);
            const textWidth = Math.ceil(Math.min(maxTextWidth, Math.max(...lines.map((line) => this.estimateTextWidth(line, fontSize)))));
            const bubbleWidth = Math.max(minBubbleWidth, Math.ceil(textWidth + paddingX * 2));
            const bubbleHeight = Math.max(38, Math.ceil(lines.length * lineHeight + paddingY * 2));

            return {
                bubbleHeight,
                bubbleWidth,
                isUser,
                lines,
                textWidth,
            };
        });

        let totalHeight = visible.reduce((sum, item, index) => sum + item.bubbleHeight + (index > 0 ? gap : 0), 0);
        while (visible.length > 1 && totalHeight > chatAreaHeight - 16) {
            visible.shift();
            totalHeight = visible.reduce((sum, item, index) => sum + item.bubbleHeight + (index > 0 ? gap : 0), 0);
        }

        let cursorTop = chatAreaHeight / 2 - 16;
        visible.forEach((item, index) => {
            const bubble = this.createGraphicsNode(`Chat_${index}`, this.chatLogRoot);
            const x = item.isUser ? rightX - item.bubbleWidth / 2 : leftX + item.bubbleWidth / 2;
            const y = cursorTop - item.bubbleHeight / 2;
            bubble.setPosition(x, y, 0);
            bubble.addComponent(UITransform).setContentSize(item.bubbleWidth, item.bubbleHeight);
            const g = bubble.getComponent(Graphics)!;
            this.roundRect(
                g,
                -item.bubbleWidth / 2,
                -item.bubbleHeight / 2,
                item.bubbleWidth,
                item.bubbleHeight,
                6,
                item.isUser ? new Color(40, 44, 48, 255) : new Color(28, 31, 34, 255),
                new Color(82, 88, 92, 255),
            );

            const label = this.createLabel(item.lines.join('\n'), fontSize, item.isUser ? new Color(236, 238, 240, 255) : new Color(190, 196, 202, 255), item.textWidth);
            label.setParent(bubble);
            label.setPosition(0, 0, 0);
            label.getComponent(UITransform)!.setContentSize(item.textWidth, item.lines.length * lineHeight);
            const labelComponent = label.getComponent(Label)!;
            labelComponent.horizontalAlign = Label.HorizontalAlign.LEFT;
            labelComponent.verticalAlign = Label.VerticalAlign.CENTER;
            labelComponent.lineHeight = lineHeight;
            labelComponent.enableWrapText = true;
            labelComponent.overflow = Label.Overflow.RESIZE_HEIGHT;
            cursorTop -= item.bubbleHeight + gap;
        });
    }

    private normalizeChatText(text: string) {
        const normalized = text
            .replace(/\r\n/g, '\n')
            .replace(/\r/g, '\n')
            .replace(/[ \t]+/g, ' ')
            .trim();
        return normalized || '(空消息)';
    }

    private wrapTextToWidth(text: string, maxWidth: number, fontSize: number) {
        const lines: string[] = [];
        text.split('\n').forEach((paragraph) => {
            if (!paragraph) {
                lines.push('');
                return;
            }

            let current = '';
            this.tokenizeTextForWrap(paragraph).forEach((token) => {
                if (/^\s+$/.test(token)) {
                    if (current && this.estimateTextWidth(`${current} `, fontSize) <= maxWidth) {
                        current += ' ';
                    }
                    return;
                }

                let remaining = token;
                while (remaining) {
                    const candidate = `${current}${remaining}`;
                    if (this.estimateTextWidth(candidate, fontSize) <= maxWidth) {
                        current = candidate;
                        remaining = '';
                        continue;
                    }

                    if (current) {
                        lines.push(this.trimLineEnd(current));
                        current = '';
                        continue;
                    }

                    const split = this.takeTextThatFits(remaining, maxWidth, fontSize);
                    lines.push(split.line);
                    remaining = split.remaining;
                }
            });

            if (current) {
                lines.push(this.trimLineEnd(current));
            }
        });

        return lines.length > 0 ? lines : [''];
    }

    private trimLineEnd(text: string) {
        return text.replace(/\s+$/u, '');
    }

    private tokenizeTextForWrap(text: string) {
        return text.match(/[A-Za-z0-9_./:@#?=&%+\-]+|\s+|./gu) ?? [];
    }

    private takeTextThatFits(text: string, maxWidth: number, fontSize: number) {
        const chars = Array.from(text);
        let width = 0;
        let count = 0;
        for (const char of chars) {
            const charWidth = this.estimateTextWidth(char, fontSize);
            if (count > 0 && width + charWidth > maxWidth) {
                break;
            }
            width += charWidth;
            count += 1;
        }

        const safeCount = Math.max(1, count);
        return {
            line: chars.slice(0, safeCount).join(''),
            remaining: chars.slice(safeCount).join(''),
        };
    }

    private estimateTextWidth(text: string, fontSize: number) {
        return Array.from(text).reduce((sum, char) => sum + this.estimateCharWidth(char, fontSize), 0);
    }

    private estimateCharWidth(char: string, fontSize: number) {
        const codePoint = char.codePointAt(0) ?? 0;
        if (char === ' ') {
            return fontSize * 0.34;
        }
        if (codePoint >= 0x2e80) {
            return fontSize;
        }
        if (/[A-Z]/.test(char)) {
            return fontSize * 0.68;
        }
        if (/[a-z0-9]/.test(char)) {
            return fontSize * 0.56;
        }
        if (/[.,:;!'`|]/.test(char)) {
            return fontSize * 0.32;
        }
        if (/[-_/\\()[\]{}]/.test(char)) {
            return fontSize * 0.46;
        }
        return fontSize * 0.62;
    }

    private createSmallButton(text: string, onClick: () => void) {
        const node = this.createGraphicsNode(`SmallButton_${text}`);
        node.addComponent(UITransform).setContentSize(72, 38);
        const g = node.getComponent(Graphics)!;
        this.roundRect(g, -36, -19, 72, 38, 5, new Color(30, 33, 36, 255), new Color(82, 88, 92, 255));

        const label = this.createLabel(text, 15, new Color(236, 238, 240, 255), 62);
        label.setParent(node);
        label.setPosition(0, 0, 0);

        const button = node.addComponent(Button);
        button.transition = Button.Transition.SCALE;
        button.zoomScale = 1.025;
        button.duration = 0.08;
        node.on(Node.EventType.TOUCH_END, (event: EventTouch) => {
            onClick();
            event.propagationStopped = true;
        }, this);
        return node;
    }

    private closeSettingsPanel() {
        if (this.settingsPanel?.isValid) {
            this.settingsPanel.destroy();
        }
        this.settingsPanel = null;
    }

    private closeTestsPanel() {
        if (this.testsPanel?.isValid) {
            this.testsPanel.destroy();
        }
        this.testsPanel = null;
    }

    private closeLlmChatPanel() {
        if (this.llmChatPanel?.isValid) {
            this.llmChatPanel.destroy();
        }
        this.llmChatPanel = null;
        this.chatInput = null;
        this.chatLogRoot = null;
        this.backendStatusLabel = null;
    }

    private createSettingRow(parent: Node, name: string, value: string, y: number, onClick?: () => void) {
        const row = this.createGraphicsNode(`Setting_${name}`, parent);
        row.setPosition(0, y, 0);
        row.addComponent(UITransform).setContentSize(272, 42);
        const g = row.getComponent(Graphics)!;
        this.roundRect(g, -136, -21, 272, 42, 5, new Color(30, 33, 36, 255), new Color(82, 88, 92, 255));

        const nameLabel = this.createLabel(name, 15, new Color(214, 218, 220, 255), 110);
        nameLabel.setParent(row);
        nameLabel.setPosition(-72, 0, 0);
        nameLabel.getComponent(Label)!.horizontalAlign = Label.HorizontalAlign.LEFT;

        const valueLabel = this.createLabel(value, 14, new Color(154, 160, 166, 255), 150);
        valueLabel.setParent(row);
        valueLabel.setPosition(54, 0, 0);
        valueLabel.getComponent(Label)!.horizontalAlign = Label.HorizontalAlign.RIGHT;

        if (onClick) {
            const button = row.addComponent(Button);
            button.transition = Button.Transition.SCALE;
            button.zoomScale = 1.015;
            button.duration = 0.08;
            row.on(Node.EventType.TOUCH_END, (event: EventTouch) => {
                onClick();
                event.propagationStopped = true;
            }, this);
        }

        return valueLabel.getComponent(Label)!;
    }

    private cycleLlmProvider() {
        const currentIndex = LLM_PROVIDER_OPTIONS.findIndex((provider) => provider.id === this.llmSettings.providerId);
        const next = LLM_PROVIDER_OPTIONS[(currentIndex + 1 + LLM_PROVIDER_OPTIONS.length) % LLM_PROVIDER_OPTIONS.length];
        this.llmSettings = { ...this.llmSettings, providerId: next.id };
        saveLlmSettings(this.llmSettings);
        if (this.llmProviderValueLabel) {
            this.llmProviderValueLabel.string = this.getProviderLabel();
        }
        this.setStatus(`LLM 服务已切换为 ${next.label}`);
    }

    private cycleLlmQuality() {
        const currentIndex = LLM_QUALITY_OPTIONS.findIndex((quality) => quality.id === this.llmSettings.quality);
        const next = LLM_QUALITY_OPTIONS[(currentIndex + 1 + LLM_QUALITY_OPTIONS.length) % LLM_QUALITY_OPTIONS.length];
        this.llmSettings = { ...this.llmSettings, quality: next.id };
        saveLlmSettings(this.llmSettings);
        if (this.llmQualityValueLabel) {
            this.llmQualityValueLabel.string = this.getQualityLabel();
        }
        this.setStatus(`模型档位已切换为 ${next.label}`);
    }

    private getProviderLabel() {
        return LLM_PROVIDER_OPTIONS.find((provider) => provider.id === this.llmSettings.providerId)?.label ?? 'ChatGPT';
    }

    private getQualityLabel() {
        return LLM_QUALITY_OPTIONS.find((quality) => quality.id === this.llmSettings.quality)?.label ?? 'Standard';
    }

    private handleAction(action: MenuAction) {
        switch (action) {
            case 'start':
                this.setStatus('正在启动新的小镇');
                if (this.gameSceneName) {
                    director.loadScene(this.gameSceneName);
                }
                break;
            case 'continue':
                this.continueGame();
                break;
            case 'tests':
                this.openLlmChatPanel();
                break;
            case 'settings':
                this.toggleSettings();
                break;
            case 'exit':
                this.setStatus('正在退出游戏');
                game.end();
                break;
        }
    }

    private continueGame() {
        const saveData = sys.localStorage.getItem(this.saveKey);
        if (!saveData) {
            this.setStatus('暂无可读取的存档');
            return;
        }

        this.setStatus('正在读取小镇存档');
        if (this.gameSceneName) {
            director.loadScene(this.gameSceneName);
        }
    }

    private createLabel(text: string, fontSize: number, color: Color, width = 620) {
        const node = new Node(text);
        node.layer = Layers.Enum.UI_2D;
        node.addComponent(UITransform).setContentSize(width, fontSize + 14);

        const label = node.addComponent(Label);
        label.string = text;
        label.fontSize = fontSize;
        label.lineHeight = fontSize + 8;
        label.color = color;
        label.horizontalAlign = Label.HorizontalAlign.CENTER;
        label.verticalAlign = Label.VerticalAlign.CENTER;
        return node;
    }

    private createGraphicsNode(name: string, parent?: Node | null) {
        const node = new Node(name);
        node.layer = Layers.Enum.UI_2D;
        node.addComponent(Graphics);
        if (parent) {
            node.setParent(parent);
        }
        return node;
    }

    private drawMoon(g: Graphics, x: number, y: number) {
        g.fillColor = new Color(249, 215, 139, 255);
        g.circle(x, y, 34);
        g.fill();
        g.fillColor = new Color(24, 38, 51, 255);
        g.circle(x + 14, y + 8, 30);
        g.fill();
    }

    private drawPixelTown(g: Graphics) {
        const baseY = -118;
        this.drawBuilding(g, -448, baseY, 86, 152, new Color(64, 86, 92, 255), new Color(238, 174, 87, 255));
        this.drawBuilding(g, -344, baseY, 72, 116, new Color(88, 86, 73, 255), new Color(132, 196, 151, 255));
        this.drawBuilding(g, -250, baseY, 92, 172, new Color(75, 68, 84, 255), new Color(236, 174, 88, 255));
        this.drawBuilding(g, -132, baseY, 76, 126, new Color(69, 103, 91, 255), new Color(229, 126, 84, 255));
        this.drawTree(g, -500, -144);
        this.drawTree(g, -92, -144);
        this.drawTree(g, 12, -144);
    }

    private drawBuilding(g: Graphics, x: number, y: number, width: number, height: number, color: Color, light: Color) {
        this.fillRect(g, x, y, width, height, color);
        this.fillRect(g, x - 4, y + height, width + 8, 10, new Color(38, 47, 54, 255));

        for (let row = 0; row < 3; row++) {
            for (let col = 0; col < 2; col++) {
                this.fillRect(g, x + 16 + col * 30, y + 24 + row * 36, 14, 18, row === 1 && col === 0 ? light : new Color(27, 40, 45, 255));
            }
        }
    }

    private drawTree(g: Graphics, x: number, y: number) {
        this.fillRect(g, x - 5, y - 8, 10, 26, new Color(103, 73, 52, 255));
        this.fillRect(g, x - 20, y + 10, 40, 28, new Color(59, 121, 89, 255));
        this.fillRect(g, x - 14, y + 32, 28, 18, new Color(83, 154, 102, 255));
    }

    private drawRoad(g: Graphics) {
        this.fillRect(g, -960, -260, 1920, 120, new Color(48, 52, 50, 255));
        for (let x = -900; x < 900; x += 94) {
            this.fillRect(g, x, -206, 42, 6, new Color(219, 184, 116, 180));
        }
    }

    private drawAtmosphere(g: Graphics) {
        for (let i = 0; i < 16; i++) {
            const x = -510 + i * 74;
            const y = 244 - (i % 5) * 38;
            this.fillRect(g, x, y, 3, 3, new Color(216, 229, 214, 140));
        }
    }

    private fillRect(g: Graphics, x: number, y: number, width: number, height: number, color: Color) {
        g.fillColor = color;
        g.rect(x, y, width, height);
        g.fill();
    }

    private roundRect(g: Graphics, x: number, y: number, width: number, height: number, radius: number, fill: Color, stroke?: Color) {
        g.fillColor = fill;
        g.roundRect(x, y, width, height, radius);
        g.fill();
        if (stroke) {
            g.strokeColor = stroke;
            g.lineWidth = 2;
            g.roundRect(x, y, width, height, radius);
            g.stroke();
        }
    }

    private setStatus(message: string) {
        if (this.statusLabel) {
            this.statusLabel.string = message;
        }
        console.log(`[MainMenu] ${message}`);
    }

    private ensureFullScreen(node: Node) {
        let transform = node.getComponent(UITransform);
        if (!transform) {
            transform = node.addComponent(UITransform);
        }
        transform.setContentSize(960, 640);

        let widget = node.getComponent(Widget);
        if (!widget) {
            widget = node.addComponent(Widget);
        }
        widget.isAlignLeft = true;
        widget.isAlignRight = true;
        widget.isAlignTop = true;
        widget.isAlignBottom = true;
        widget.left = 0;
        widget.right = 0;
        widget.top = 0;
        widget.bottom = 0;
        widget.alignMode = Widget.AlignMode.ON_WINDOW_RESIZE;
    }

    private onKeyDown(event: { keyCode: KeyCode }) {
        if (event.keyCode === KeyCode.ESCAPE) {
            if (this.llmChatPanel?.isValid) {
                this.closeLlmChatPanel();
                return;
            }
            if (this.testsPanel?.isValid) {
                this.closeTestsPanel();
                return;
            }
            if (this.settingsPanel?.isValid) {
                this.toggleSettings();
            }
        }
    }
}
