# SVN to Git Ignore Converter

一个高效的工具，用于将Subversion的svn:ignore属性配置转换为等价的.gitignore配置。

## 功能特点

- 一次性批量收集所有目录的svn:ignore属性，极大提升性能
- 自动转换为.gitignore格式，路径分隔符统一为/
- 支持递归处理子目录，并可通过`--max-depth`限制递归深度
- 支持导出到指定文件
- 支持多线程并发处理（`--threads`，最大10线程）
- 跳过被父目录ignore规则忽略的子目录，进一步提升效率
- 详细进度与耗时统计，便于大项目下的使用体验

## 安装要求

- Python 3.6+
- SVN命令行工具（需支持`svn propget -R`）

## 安装步骤

1. 克隆仓库：
```bash
git clone [repository-url]
cd svn-git-ignore-converter
```

2. 创建并激活虚拟环境：
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

## 使用方法

基本用法：
```bash
python svn2git_ignore.py convert /path/to/svn/repo
```

可选参数：
- `--output-file`：指定输出文件路径（默认为当前目录的.gitignore）
- `--recursive`：递归处理子目录（默认：False）
- `--max-depth`：递归的最大深度（0为不限制）
- `--threads`：并行线程数（最大10，默认4）

示例：
```bash
# 转换单个目录的ignore配置
python svn2git_ignore.py convert ./my_svn_project

# 递归处理所有子目录，最大递归深度为3，使用8线程并发
python svn2git_ignore.py convert ./my_svn_project --recursive --max-depth 3 --threads 8 --output-file .gitignore
```

## 性能说明
- 工具会先批量收集所有有svn:ignore属性的目录，极大减少SVN命令调用次数
- 多线程并发处理，适合大规模项目
- 跳过被父目录ignore规则忽略的目录，进一步提升效率
- 控制台会显示收集目录和实际处理的耗时，便于性能评估

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件
