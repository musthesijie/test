# 安保服装库存系统

一个面向保安公司的轻量级服装出入库与发放管理工具，基于 SQLite 和命令行即可运行，无需额外依赖。可用于记录制服、鞋帽、装备等物资的入库、发放、归还及盘点调整。

## 功能概览
- 物资款式维护：名称、尺码、类别、安全库存下限。
- 员工档案：姓名、岗位、工牌号（可选）。
- 出入库流水：入库/补货、发放、归还、盘点调整，自动累加/扣减库存并保留历史。
- 库存视图：当前可用数量与低于安全库存的预警标识。
- 历史查询：按物资或员工过滤，支持审计追溯。

## 快速开始
1. 初始化数据库（会在仓库根目录生成 `inventory.db`）：
   ```bash
   python -m inventory_system.cli init
   ```
2. 录入款式与员工：
   ```bash
   python -m inventory_system.cli add-item "制服衬衫" --size L --category 夏季 --min-stock 20
   python -m inventory_system.cli add-employee "张三" --role 班长 --badge 10086
   ```
3. 日常操作：
   ```bash
   # 入库/补货
   python -m inventory_system.cli stock-in "制服衬衫" --size L --category 夏季 --quantity 50 --note "季度补货"

   # 发放与归还
   python -m inventory_system.cli issue "制服衬衫" --size L --category 夏季 --to "张三" --quantity 2 --note "入职发放"
   python -m inventory_system.cli return "制服衬衫" --size L --category 夏季 --from "张三" --quantity 1 --note "换季归还"

   # 盘点调整（正数增加，负数减少）
   python -m inventory_system.cli adjust "制服衬衫" --size L --category 夏季 --quantity -1 --note "盘亏"
   ```
4. 查看数据：
   ```bash
   # 当前库存与预警
   python -m inventory_system.cli status

   # 出入库历史
   python -m inventory_system.cli history
   python -m inventory_system.cli history --name 衬衫
   python -m inventory_system.cli history --employee 张三
   ```

## 设计要点
- **SQLite 本地存储**：便携文件数据库，适合小团队快速落地，可后续迁移到其他数据库。
- **最小依赖**：只使用标准库，方便在无网络环境下部署。
- **安全库存**：`status` 命令会对低于 `min_stock` 的款式显示预警，便于及时补货。
- **可扩展性**：可在 `transactions` 表上增加审批字段或附件路径，以满足领用审批、签收单等需求。

## 目录结构
```
inventory_system/
  __init__.py        # 包声明
  db.py              # SQLite 连接与表结构
  operations.py      # 业务逻辑：员工、物资、流水、报表
  cli.py             # 命令行入口
```

## 后续改进建议
- 增加命令测试（例如使用 `pytest`）保障逻辑正确性。
- 为高频操作提供二维码或条码扫描接口。
- 增加导出 CSV/Excel 的接口，便于和财务或人事系统对接。
