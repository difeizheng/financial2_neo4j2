# 财务模型知识图谱系统

将 Excel 财务模型解析为知识图谱，支持公式依赖传播和 D3.js 可视化。

## 功能特性

- **Excel 解析**：提取单元格、公式、合并单元格，构建知识图谱
- **公式求值**：支持跨 sheet 公式依赖和值传播模拟
- **D3.js 可视化**：图谱浏览 + 波浪式传播动画
- **LLM 集成**：语义标注、结构识别、异常检测（支持多后端）

## 技术栈

- Python 3.10+
- Streamlit (Web UI)
- D3.js (可视化)
- openpyxl (Excel 解析)
- SQLite (任务管理)

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 配置 LLM
cp .env.example .env
# 编辑 .env 填入 API Key

# 启动应用
streamlit run financial_kg/web/app.py
```

## 目录结构

```
financial_kg/
├── core/           # 解析引擎、公式求值、传播计算
├── llm/            # LLM 集成（多后端路由）
├── web/            # Streamlit UI
│   ├── pages/      # 各页面（上传、图谱浏览、解析状态）
│   └── components/ # D3.js 自定义组件
├── storage/        # JSON 导出、SQLite 任务管理
└── models/         # 数据模型定义
```

## 使用流程

1. **上传 Excel**：选择要解析的 sheet（建议先选 4 个验证）
2. **解析**：系统提取单元格、公式，构建依赖 DAG
3. **图谱浏览**：D3.js 可视化，支持搜索、过滤
4. **值传播模拟**：修改参数后查看波浪式传播动画

## 版本历史

- **v1.0.0** (2026-04-20)：首批 4 个 sheet 解析、传播动画、LLM 集成

## License

MIT