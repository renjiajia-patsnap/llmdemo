# 声音克隆工具

这是一个基于阿里云通义千问的CosyVoice服务的声音克隆工具。该工具可以从音频文件URL克隆声音，并使用克隆的声音合成语音。

## 功能特点

- 从音频URL克隆声音
- 使用克隆的声音合成文本为语音
- 列出已克隆的所有声音
- 删除不需要的声音
- 支持命令行操作
- 完善的日志记录
- 异常处理机制

## 安装

### 前提条件

- Python 3.8 或更高版本
- 阿里云通义千问API密钥

### 依赖项安装

```bash
pip install dashscope python-dotenv
```

### 环境变量配置

创建一个 `.env` 文件，并添加以下内容：

```
TONGYI_API_KEY=your_api_key_here
```

## 使用方法

### 1. 克隆新声音

从音频URL创建新的声音克隆：

```bash
python clone_my_voice.py clone --url "<音频文件URL>" --prefix "<声音前缀>"
```

示例：
```bash
python clone_my_voice.py clone --url "https://example.com/my_voice.mp3" --prefix "myvoice"
```

> **注意**：每次调用都会创建新的声音，阿里云账号最多支持1000个声音。请避免重复克隆同一个声音。

### 2. 合成语音

使用已克隆的声音ID合成文本为语音：

```bash
python clone_my_voice.py synthesize --voice-id "<声音ID>" --text "<要合成的文本>" --output "<输出文件路径>"
```

示例：
```bash
python clone_my_voice.py synthesize --voice-id "cosyvoice-v2-myvoice-123456" --text "今天天气真不错" --output "weather.mp3"
```

### 3. 列出所有声音

列出账号下所有可用的克隆声音：

```bash
python clone_my_voice.py list-voices
```

### 4. 删除声音

删除不再需要的声音：

```bash
python clone_my_voice.py delete-voice --voice-id "<声音ID>"
```

示例：
```bash
python clone_my_voice.py delete-voice --voice-id "cosyvoice-v2-myvoice-123456"
```

### 5. 一站式流程

一次性完成声音克隆和语音合成：

```bash
python clone_my_voice.py clone-and-synthesize --url "<音频文件URL>" --prefix "<声音前缀>" --text "<要合成的文本>" --output "<输出文件路径>"
```

示例：
```bash
python clone_my_voice.py clone-and-synthesize --url "https://example.com/my_voice.mp3" --prefix "myvoice" --text "大家好，这是我的克隆声音" --output "greeting.mp3"
```

## 注意事项

1. 音频文件要求：
   - 格式：支持MP3、WAV等常见格式
   - 时长：建议3-10分钟的清晰语音
   - 质量：背景噪音少，声音清晰

2. 声音ID限制：
   - 每个阿里云账号最多可克隆1000个声音
   - 不需要的声音建议及时删除

3. API使用限制：
   - 使用前请查看阿里云官方文档了解最新的API使用限制和计费规则
   - 避免频繁调用API，以免产生不必要的费用

## 示例代码

### 在其他Python代码中使用

```python
from llm.clone_my_voice import VoiceCloner

# 初始化声音克隆器
cloner = VoiceCloner()

# 克隆声音
voice_id = cloner.clone_voice(
    audio_url="https://example.com/my_voice.mp3",
    prefix="myvoice"
)

# 合成语音
cloner.synthesize_speech(
    voice_id=voice_id,
    text="这是使用我的声音合成的语音",
    output_file="my_synthesized_voice.mp3"
)
```

## 开发计划

- [ ] 添加本地音频文件支持
- [ ] 实现批量文本合成功能
- [ ] 添加Web界面
- [ ] 支持更多语音合成参数（语速、音量等）

## 参考文档

- [阿里云通义千问CosyVoice API文档](https://help.aliyun.com/zh/model-studio/cosyvoice-clone-api)
- [Dashscope Python SDK文档](https://help.aliyun.com/document_detail/656523.html) 