"""
旧 monolith 数据迁移脚本草案（目标：本仓库 backend/）

用法示例：
python manage.py shell < scripts/migrate_from_old_backend.py
"""

print("数据迁移脚本待接入。")
print("建议迁移顺序：Tag -> Platform -> Business -> SKU -> QuickPhrase")
print("建议在确认 backend 模型与页面稳定后，再正式实现该脚本。")
