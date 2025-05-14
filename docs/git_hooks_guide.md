# Git提交钩子使用指南

本指南介绍如何使用项目中的Git提交钩子功能，该功能可以在提交代码前自动分析代码变更，提供质量评估和安全建议。

## 功能特点

- 🔍 自动分析提交内容，评估代码质量
- 🛡️ 检测潜在的安全问题和敏感信息
- 📝 提供优化建议和改进方向
- 📊 对提交进行评分（1-10分）
- 📜 保存分析历史记录，便于回顾
- 🚫 可配置为在发现严重问题时阻止提交

## 安装步骤

1. 确保已安装Python 3.6+及Git
2. 克隆项目后，运行安装脚本：

```bash
python utils/install_hooks.py
```

3. 安装脚本会自动：
   - 检查并安装所需依赖项
   - 创建并配置Git钩子
   - 更新requirements.txt（如需要）

## 配置说明

钩子的行为可通过`config/git_hook_config.yaml`文件配置，主要配置项包括：

### 模型设置

```yaml
model:
  # 使用的模型类型: openai, tongyi, deepseek
  type: openai
  # 使用的模型名称
  name: gpt-3.5-turbo
  # 超时设置(秒)
  timeout: 30
```

### 分析设置

```yaml
analysis:
  # 是否启用分析
  enabled: true
  # 分析级别：basic(基本), comprehensive(全面), security_focused(安全重点)
  level: comprehensive
  # 是否在分析中包含评分机制
  include_rating: true
  # 最大分析差异大小限制（字节），超过此值会截断
  max_diff_size: 50000
  # 提交消息最小长度要求
  min_commit_message_length: 10
```

### 行为设置

```yaml
behavior:
  # 是否记录历史
  save_history: true
  # 是否遇到严重问题时阻止提交
  block_on_critical: false
  # 需要关注的特定文件模式（正则表达式）
  critical_file_patterns:
    - ".*password.*"
    - ".*credential.*"
    - ".*secret.*"
    - ".*key\\.py$"
  # 允许忽略的文件模式
  ignored_file_patterns:
    - ".*\\.md$"
    - ".*\\.json$"
    - ".*\\.log$"
    - "^docs/.*"
```

### 输出设置

```yaml
output:
  # 是否使用颜色输出
  colorize: true
  # 是否包含emoji
  use_emoji: true
  # 输出详细程度: minimal, normal, verbose
  verbosity: normal
  # 是否显示提示和帮助信息
  show_tips: true
```

### 历史记录设置

```yaml
history:
  # 历史记录文件路径（相对于项目根目录）
  file_path: logs/commit_analysis.json
  # 默认导出路径
  export_path: logs/commit_analysis.md
  # 最大保存记录数（0表示不限制）
  max_records: 100
```

## 环境变量

需要设置以下环境变量：

- `OPENAI_API_KEY`：如果使用OpenAI模型，需要设置API密钥

可以通过以下方式设置环境变量：

- Linux/macOS: `export OPENAI_API_KEY=your-api-key`
- Windows (CMD): `set OPENAI_API_KEY=your-api-key`
- Windows (PowerShell): `$env:OPENAI_API_KEY="your-api-key"`

也可以将这些变量添加到`.env`文件中（需确保该文件已在`.gitignore`中）。

## 使用方法

安装完成后，钩子会在以下情况自动运行：

1. 当执行`git commit`命令时
2. 钩子会分析暂存的更改并提供反馈
3. 如果配置为在发现严重问题时阻止提交，它会阻止提交并显示错误信息

## 历史记录

分析结果会保存在`logs/commit_analysis.json`中，同时会生成一个易读的Markdown版本在`logs/commit_analysis.md`。

## 常见问题

### 禁用钩子

如果需要临时跳过钩子检查，可以使用`--no-verify`参数：

```bash
git commit -m "紧急修复" --no-verify
```

但强烈建议仅在特殊情况下使用此选项。

### 钩子不运行

确保：
1. 安装脚本成功执行
2. 钩子文件具有可执行权限
3. 配置文件中`analysis.enabled`设置为`true`

### 更新钩子

如果需要更新钩子，只需再次运行安装脚本：

```bash
python utils/install_hooks.py
```

## 最佳实践

1. 提交前先运行自动化测试
2. 撰写清晰具体的提交信息
3. 每次提交专注于单一功能或修复
4. 不要在代码中包含敏感信息
5. 定期查看分析历史，总结改进方向 