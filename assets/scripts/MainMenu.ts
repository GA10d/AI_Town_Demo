import {
    _decorator,
    Button,
    Color,
    Component,
    director,
    EventTouch,
    game,
    Graphics,
    input,
    Input,
    KeyCode,
    Label,
    Layers,
    Node,
    sys,
    tween,
    UITransform,
    UIOpacity,
    Vec3,
    Widget,
} from 'cc';

const { ccclass, property } = _decorator;

type MenuAction = 'start' | 'continue' | 'settings' | 'exit';

interface MenuButtonTheme {
    fill: Color;
    stroke: Color;
    text: Color;
    accent: Color;
}

@ccclass('MainMenu')
export class MainMenu extends Component {
    @property
    public gameSceneName = '';

    @property
    public saveKey = 'aitown-save';

    private menuRoot: Node | null = null;
    private settingsPanel: Node | null = null;
    private statusLabel: Label | null = null;

    private readonly normalButton: MenuButtonTheme = {
        fill: new Color(39, 54, 61, 246),
        stroke: new Color(109, 145, 132, 255),
        text: new Color(239, 245, 233, 255),
        accent: new Color(236, 174, 88, 255),
    };

    private readonly activeButton: MenuButtonTheme = {
        fill: new Color(59, 91, 88, 255),
        stroke: new Color(238, 197, 116, 255),
        text: new Color(255, 250, 226, 255),
        accent: new Color(255, 211, 128, 255),
    };

    start() {
        this.node.layer = Layers.Enum.UI_2D;
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
        this.createFooter();
    }

    private createBackground() {
        const bg = this.createGraphicsNode('Background', this.menuRoot);
        this.ensureFullScreen(bg);

        const g = bg.getComponent(Graphics)!;
        this.fillRect(g, -960, -540, 1920, 1080, new Color(15, 23, 31, 255));

        this.fillRect(g, -960, -140, 1920, 680, new Color(24, 38, 51, 255));
        this.fillRect(g, -960, -540, 1920, 400, new Color(28, 48, 43, 255));
        this.fillRect(g, -960, -126, 1920, 16, new Color(236, 174, 88, 210));

        this.drawMoon(g, -398, 204);
        this.drawPixelTown(g);
        this.drawRoad(g);
        this.drawAtmosphere(g);
    }

    private createBrandBlock() {
        if (!this.menuRoot) {
            return;
        }

        const kicker = this.createLabel('GENERATIVE TOWN SIM', 16, new Color(236, 174, 88, 255), 420);
        kicker.setParent(this.menuRoot);
        kicker.setPosition(-252, 176, 0);
        kicker.getComponent(Label)!.horizontalAlign = Label.HorizontalAlign.LEFT;

        const title = this.createLabel('AI TOWN', 64, new Color(248, 250, 236, 255), 470);
        title.name = 'Title';
        title.setParent(this.menuRoot);
        title.setPosition(-252, 118, 0);
        title.getComponent(Label)!.horizontalAlign = Label.HorizontalAlign.LEFT;
        title.getComponent(Label)!.lineHeight = 68;

        const cnTitle = this.createLabel('智能体小镇', 28, new Color(201, 225, 209, 255), 420);
        cnTitle.setParent(this.menuRoot);
        cnTitle.setPosition(-252, 62, 0);
        cnTitle.getComponent(Label)!.horizontalAlign = Label.HorizontalAlign.LEFT;

        const description = this.createLabel('居民拥有记忆、目标和日程。每一天，都由后端智能体驱动。', 18, new Color(169, 194, 187, 255), 500);
        description.setParent(this.menuRoot);
        description.setPosition(-212, 16, 0);
        description.getComponent(Label)!.horizontalAlign = Label.HorizontalAlign.LEFT;

        const badge = this.createGraphicsNode('LiveBadge', this.menuRoot);
        badge.setPosition(-358, -46, 0);
        const g = badge.getComponent(Graphics)!;
        this.roundRect(g, -118, -24, 236, 48, 8, new Color(25, 37, 40, 235), new Color(93, 131, 117, 255));
        this.fillRect(g, -96, -5, 10, 10, new Color(111, 211, 139, 255));

        const badgeText = this.createLabel('SIMULATION READY', 15, new Color(215, 231, 219, 255), 190);
        badgeText.setParent(badge);
        badgeText.setPosition(18, 0, 0);
    }

    private createMenuPanel() {
        if (!this.menuRoot) {
            return;
        }

        const panel = this.createGraphicsNode('MenuPanel', this.menuRoot);
        panel.setPosition(256, 4, 0);
        panel.addComponent(UITransform).setContentSize(360, 420);

        const g = panel.getComponent(Graphics)!;
        this.roundRect(g, -180, -210, 360, 420, 10, new Color(21, 31, 38, 238), new Color(88, 122, 118, 255));
        this.fillRect(g, -148, 152, 296, 2, new Color(236, 174, 88, 255));

        const title = this.createLabel('主菜单', 28, new Color(244, 248, 234, 255), 280);
        title.setParent(panel);
        title.setPosition(0, 176, 0);

        const entries: Array<[string, string, MenuAction]> = [
            ['开始游戏', '建立新的小镇日程', 'start'],
            ['继续游戏', '读取本地存档状态', 'continue'],
            ['设置', '音量、画面和调试选项', 'settings'],
            ['退出游戏', '关闭当前客户端', 'exit'],
        ];

        entries.forEach(([text, detail, action], index) => {
            const button = this.createMenuButton(text, detail, action);
            button.setParent(panel);
            button.setPosition(0, 104 - index * 76, 0);
        });

        const statusNode = this.createLabel('请选择一项操作', 15, new Color(151, 174, 166, 255), 280);
        statusNode.name = 'Status';
        statusNode.setParent(panel);
        statusNode.setPosition(0, -178, 0);
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

    private createMenuButton(text: string, detail: string, action: MenuAction) {
        const node = this.createGraphicsNode(`Button_${action}`);
        node.addComponent(UIOpacity).opacity = 250;
        node.addComponent(UITransform).setContentSize(296, 62);
        this.drawButton(node, this.normalButton);

        const button = node.addComponent(Button);
        button.transition = Button.Transition.SCALE;
        button.zoomScale = 1.025;
        button.duration = 0.08;

        const label = this.createLabel(text, 22, this.normalButton.text, 210);
        label.name = 'Label';
        label.setParent(node);
        label.setPosition(-16, 9, 0);
        label.getComponent(Label)!.horizontalAlign = Label.HorizontalAlign.LEFT;

        const detailLabel = this.createLabel(detail, 13, new Color(150, 171, 164, 255), 210);
        detailLabel.name = 'Detail';
        detailLabel.setParent(node);
        detailLabel.setPosition(-16, -16, 0);
        detailLabel.getComponent(Label)!.horizontalAlign = Label.HorizontalAlign.LEFT;

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
        this.roundRect(g, -148, -31, 296, 62, 8, theme.fill, theme.stroke);
        this.fillRect(g, -148, -31, 6, 62, theme.accent);
        this.fillRect(g, 118, 6, 8, 8, theme.accent);
        this.fillRect(g, 130, 6, 8, 8, new Color(theme.accent.r, theme.accent.g, theme.accent.b, 155));
        this.fillRect(g, 124, -6, 8, 8, new Color(theme.accent.r, theme.accent.g, theme.accent.b, 100));
    }

    private toggleSettings() {
        if (this.settingsPanel?.isValid) {
            this.settingsPanel.destroy();
            this.settingsPanel = null;
            this.setStatus('设置已关闭');
            return;
        }

        const panel = this.createGraphicsNode('SettingsPanel', this.menuRoot);
        panel.setPosition(256, 4, 0);
        panel.addComponent(UITransform).setContentSize(360, 420);
        panel.addComponent(UIOpacity).opacity = 0;

        const g = panel.getComponent(Graphics)!;
        this.roundRect(g, -180, -210, 360, 420, 10, new Color(18, 28, 34, 252), new Color(236, 174, 88, 255));
        this.fillRect(g, -148, 152, 296, 2, new Color(236, 174, 88, 255));

        const title = this.createLabel('设置', 30, new Color(248, 250, 236, 255), 280);
        title.setParent(panel);
        title.setPosition(0, 176, 0);

        this.createSettingRow(panel, '音量', '100%', 88);
        this.createSettingRow(panel, '窗口模式', '网页发布时接入', 34);
        this.createSettingRow(panel, '调试信息', '可显示智能体状态', -20);

        const close = this.createMenuButton('关闭', '返回主菜单', 'settings');
        close.setParent(panel);
        close.setScale(new Vec3(0.82, 0.82, 1));
        close.setPosition(0, -132, 0);

        this.settingsPanel = panel;
        tween(panel.getComponent(UIOpacity)!).to(0.16, { opacity: 255 }).start();
        this.setStatus('设置已打开');
    }

    private createSettingRow(parent: Node, name: string, value: string, y: number) {
        const row = this.createGraphicsNode(`Setting_${name}`, parent);
        row.setPosition(0, y, 0);
        const g = row.getComponent(Graphics)!;
        this.roundRect(g, -136, -21, 272, 42, 6, new Color(31, 45, 50, 235), new Color(70, 96, 92, 255));

        const nameLabel = this.createLabel(name, 17, new Color(200, 220, 210, 255), 110);
        nameLabel.setParent(row);
        nameLabel.setPosition(-72, 0, 0);
        nameLabel.getComponent(Label)!.horizontalAlign = Label.HorizontalAlign.LEFT;

        const valueLabel = this.createLabel(value, 15, new Color(236, 174, 88, 255), 150);
        valueLabel.setParent(row);
        valueLabel.setPosition(54, 0, 0);
        valueLabel.getComponent(Label)!.horizontalAlign = Label.HorizontalAlign.RIGHT;
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
        if (event.keyCode === KeyCode.ESCAPE && this.settingsPanel?.isValid) {
            this.toggleSettings();
        }
    }
}
