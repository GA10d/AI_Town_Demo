# AI Town Demo

[English](README.md) | 简体中文

AI Town Demo 是一个用于探索 AI 叙事边界的实验项目。它希望把开放式 LLM 交互转化为一套可执行、可复用的游戏流程方案：提示词、结构化输出、CSV 编写的世界数据、本地美术资源和运行时行为都保持显式配置，从而让策划和程序可以在相对分离的工作流中协作，而不是把所有叙事逻辑都塞进代码或提示词里。

本项目的实现方法也受到游戏《AI2U》的启发。《AI2U》在 2023 年 3 月左右首次上线 demo。在结构化输出还远没有稳定解决方案的时期，它通过精心设计完成了令人惊艳的游戏演出效果。AI Town Demo 延续这种思路：把 AI 回复视为可被游戏读取的“叙事信号”，再由这些信号驱动清晰可控的角色行动、心情气泡和场景交互。

项目使用 Python、Pygame、Tiled 地图资源和兼容 OpenAI 接口的本地 LLM 后端构建。玩家可以在像素风小镇中移动，打开游戏内手机，与 AI 角色聊天，并让结构化 LLM 返回结果驱动世界中的行为，例如导航目标和情绪气泡。

![AI Town 主菜单](showcase/menu.png)

## Demo

<video src="showcase/AI%20town%20demo.mp4" controls width="100%"></video>

如果当前 Markdown 查看器无法直接播放视频，可以打开下面的链接：

[AI town demo.mp4](showcase/AI%20town%20demo.mp4)

## 功能亮点

- 使用 Python/Pygame 构建的客户端，支持窗口缩放和全屏切换。
- 使用项目现有资源渲染 Tiled `.tmx` 地图。
- 游戏内手机聊天接入本地 Node LLM 网关。
- AI 回复采用结构化 JSON，包含可展示回复、目标家具 id 和情绪 id。
- 家具目录和摆放信息由 CSV 驱动。
- 情绪目录由 CSV 驱动，并匹配本地像素风情绪气泡素材。
- 手机返回目标家具后，角色可以自动导航到配置好的可交互位置。
- 包含主菜单、设置面板、LLM 测试面板、本地存档/设置 JSON 和完整响应调试视图。

## 运行方式

安装 Pygame 客户端需要的 Python 依赖后，启动游戏：

```powershell
conda activate AI_Town
python python_town/main.py
```

手机聊天和 LLM 测试面板会调用本地 OpenAI-compatible 后端。在仓库根目录启动后端：

```powershell
npm install
npm run start:llm
```

默认后端地址：

```text
http://127.0.0.1:8787
```

API Key、模型和供应商配置由 Node 后端的环境变量处理。

## 操作说明

- `WASD`：移动角色。
- `Tab`：打开或关闭手机聊天。
- `Enter`：手机输入框聚焦时发送消息。
- `Esc`：关闭面板或返回主菜单。
- `Q/E`、`+/-` 或 `PageUp/PageDown`：缩放地图相机。
- `Home` 或 `0`：重置相机缩放。
- 拖拽窗口边框：调整游戏窗口大小。
- `F11` 或 `Alt+Enter`：切换全屏。

## 项目结构

```text
assets/                 游戏资源、地图、角色、家具和情绪素材
art/                    源美术或备用美术资源
prompt/                 LLM system prompt
python_town/            Python/Pygame 游戏客户端
python_town/data/       游戏读取的 CSV 和 JSON 数据
server/                 本地 OpenAI-compatible LLM 网关
scripts/                辅助脚本
showcase/               README 使用的截图和演示视频
```

更详细的 Python 客户端说明见：[python_town/README.md](python_town/README.md)。

## 数据驱动内容

家具定义位于：

```text
python_town/data/furniture_catalog.csv
python_town/data/furniture_placements.csv
```

情绪气泡素材和目录位于：

```text
assets/resources/emotion/
python_town/data/emotion_catalog.csv
```

手机结构化返回 schema 位于：

```text
python_town/data/phone_response_schema.json
```

运行时，手机 system prompt 会由结构化 schema、家具目录和情绪目录共同组装而成，因此 LLM 会被要求返回能够匹配本地游戏资源的 id。

## 说明

这是一个原型项目。仓库中混合了玩法系统、LLM 实验和资源工作流，很多内容都刻意做成数据驱动，方便在迭代中快速调整。

## 局限性

本项目总共的开发时长大约只有 4 个小时，因此很多地方都会比较粗糙：UI 布局、交互细节、prompt 设计、数据配置方式和运行时表现都还有很大的改进空间。

后续可能会尝试更加便捷的配表方案，也会考虑用于自动化生成可玩场景的算法。
