# scripts/

辅助脚本，将 `brands/*.md` 数据整理成方便程序调用的 JSON。

## parse_brands.py

将所有品牌 Markdown 文件解析为两个 JSON 文件：

- `data/mobile_models.json` —— 按 **品牌 → 分类 → 产品 → 型号** 嵌套的完整结构
- `data/mobile_models_flat.json` —— 扁平化清单，每个 **型号代码** 一条，方便直接查询

### 运行

```bash
# 仅需 Python 3.8+，无任何第三方依赖
python scripts/parse_brands.py

# 自定义路径或输出压缩 JSON
python scripts/parse_brands.py --brands-dir brands --out-dir data --indent 0
```

运行后会打印解析统计：

```
Parsed 43 brands, 265 categories, 6448 products, 10984 model lines, 11796 codes.
```

### 解析规则

脚本基于以下 Markdown 约定：

| 源文件结构 | 解析后字段 |
| --- | --- |
| `# 标题` | `brand.title` |
| `- key: value` (出现在第一个 `##` 之前) | `brand.meta[key] = value` |
| `## 分类名` | 一个新的 `category` |
| `**产品名:**` | 新的 `product`，无 codename / 无 internal_name |
| `` **产品名 (`codename`):** `` | `product.codename` |
| `` **[`internal_id`] 产品名 (`codename`):** `` | `product.internal_name` + `product.codename`（Apple、小米等用） |
| `` `CODE`: 描述 `` | 一个 `model`，`codes = ["CODE"]` |
| `` `CODE1` `CODE2`: 描述 `` | 一个 `model`，`codes = ["CODE1", "CODE2"]` |

对没有 `##` 顶层分类的文件（例如 `coolpad.md`），所有产品会归入名为 `_default` 的隐式分类。

## JSON 结构

### `data/mobile_models.json`

```jsonc
{
  "generated_at": "2026-05-22T07:02:12+00:00",
  "source": "https://github.com/KHwang9883/MobileModels",
  "stats": {
    "brands": 43,
    "categories": 265,
    "products": 6448,
    "models": 10984,
    "codes": 11796
  },
  "brands": [
    {
      "file": "huawei_cn",
      "title": "华为手机型号汇总",
      "meta": {
        "汇总范围": "华为 Mate/Pura/nova/...",
        "codename": "✅",
        "是否包含海外机型": "[单独汇总 (英文)](/brands/huawei_global_en.md)"
      },
      "categories": [
        {
          "name": "HUAWEI Mate 系列",
          "products": [
            {
              "name": "HUAWEI Mate 40 Pro",
              "internal_name": null,
              "codename": "Noah",
              "models": [
                {
                  "codes": ["NOH-AN00", "NOH-AN01"],
                  "description": "HUAWEI Mate 40 Pro 5G"
                },
                {
                  "codes": ["NOH-AL00", "NOH-AL10"],
                  "description": "HUAWEI Mate 40 Pro 4G"
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

### `data/mobile_models_flat.json`

每条记录代表 **一个型号代码**，便于按代码直接查询：

```jsonc
{
  "generated_at": "2026-05-22T07:02:12+00:00",
  "source": "https://github.com/KHwang9883/MobileModels",
  "stats": { "entries": 11796 },
  "entries": [
    {
      "code": "NOH-AN00",
      "description": "HUAWEI Mate 40 Pro 5G",
      "product_name": "HUAWEI Mate 40 Pro",
      "product_codename": "Noah",
      "product_internal_name": null,
      "category": "HUAWEI Mate 系列",
      "brand_file": "huawei_cn",
      "brand_title": "华为手机型号汇总"
    }
  ]
}
```

## export_php.py

将 `data/mobile_models_flat.json` 同时导出为 PHP 与 JSON 字典：

- `data/mobile_models.php`        —— PHP 数组
- `data/mobile_models_dict.json`  —— 内容相同的 JSON 对象

字段说明：

- key：型号代码 (`code`)
- value：产品名 (`product_name`)
- 重复 key 只保留首次出现的（按 `parse_brands.py` 输出顺序）

```bash
python scripts/export_php.py                       # 默认输入/输出
python scripts/export_php.py --sort                # 按 code 字典序排序
python scripts/export_php.py --php custom.php --json custom.json
```

输出大致结构：

```php
<?php

return [
    '1503-M02' => '360 手机 N4',
    'NOH-AN00' => 'HUAWEI Mate 40 Pro',
    'NOH-AN01' => 'HUAWEI Mate 40 Pro',
    // ...
];
```

```json
{
  "1503-M02": "360 手机 N4",
  "NOH-AN00": "HUAWEI Mate 40 Pro",
  "NOH-AN01": "HUAWEI Mate 40 Pro"
}
```

调用：

```php
$models = require __DIR__ . '/mobile_models.php';
echo $models['NOH-AN00']; // HUAWEI Mate 40 Pro
```

```python
import json
models = json.load(open('data/mobile_models_dict.json', encoding='utf-8'))
print(models['NOH-AN00'])  # HUAWEI Mate 40 Pro
```

## 调用示例

```python
import json
from collections import defaultdict

with open("data/mobile_models_flat.json", encoding="utf-8") as f:
    flat = json.load(f)

# 按 code 建立倒排索引（一个 code 可能存在于多个品牌文件，例如 Apple 国行/全球版本）
by_code = defaultdict(list)
for entry in flat["entries"]:
    by_code[entry["code"]].append(entry)

for hit in by_code["NOH-AN00"]:
    print(hit["brand_file"], "→", hit["description"])
```

```javascript
// Node.js
const data = require("./data/mobile_models_flat.json");
const byCode = new Map();
for (const e of data.entries) {
  if (!byCode.has(e.code)) byCode.set(e.code, []);
  byCode.get(e.code).push(e);
}
console.log(byCode.get("A1324"));
```
