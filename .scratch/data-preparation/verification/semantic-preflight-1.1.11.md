# 1.1.11 全量前语义复核

状态：全量前复核通过，不代替最终全源验收。仅依据原始元数据，不读评论、评分或模型表现决定商品去留。

41条固定代表记录通过公共CLI全部对齐：9入选、25排除、7待裁决；旧注释不改写。此前精米误待裁决和品牌蜂蜜误判的失败结果原样另存。

另读取拒绝版1.1.10中的74条完整原始元数据：每粮种成分未知条目按parent_asin的SHA-256选最低5条（不足5条全取），加全部12条完整声明条目。这是确定性非概率检查，不用于估计总体误判率，也不是逐条人工审核全部目录。范围判断使用标题、类别、features、description、details，全部原始对象仍在独立数据目录保存。

发现与有据修正（下面为实际来源位置）：

| 父商品 | 来源行 | 原文字段／依据 | 修订判定 |
|---|---:|---|---|
| B001HTISYS | 518799 | description：玉米片 `are made with simple pure ingredients - organically grown corn and sea salt` | 排除，实际加盐，不把inline made with漏作成分未知 |
| B00FWK2TFM | 296697 | description：`made with organic wheat bran flakes and plump organic raisins` | 排除，真实粮／果混合；食谱中配葡萄干不作本品配料 |
| B08XZS7VRD | 530317 | title及features：Riced Broccoli & Cauliflower，vegetable alternative、grain free | 排除，售卖蔬菜对象，不是谷物米 |
| B00JNSZK5K | 568718 | title：Live Mushroom Spawn；description：spawn on rye grains | 排除，售卖菌种，不以培养基粮种冒充原粮 |
| B0BSZXZXZP | 100693 | description：`Known as the southern oatmeal`及`preferred over oatmeal` | 待裁决，昵称／历史比较不证明燕麦身份；不据hominy自行补入粮种或处理状态 |
| B00IV6P4J2 | 292491 | features：`Rice Dishes`；title：Rice Whole Grain Spanish | 待裁决，形态定位反证保留，不推断真实调料 |
| B0078DSUV8 | 148882 | title：Whole Berry Rye；categories叶：Granola | 待裁决，类别与原粮形态反证不静默覆盖 |
| B005CD38KE | 321798 | title：Brown Rice Cereal Flakes；categories叶：Cold Cereal；明确Rice配料 | 待裁决，冷食谷物分类与A初加工形态的未解关系保留；不宣称已知熟制或实际添加 |
| B0033UE02S | 503128 | title／类别：Muesli；features：Contains famous German whole grain spelt | 待裁决，复合早餐对象不能借一个所含粮种自动确认A内售卖身份；不补真实配方 |
| B074D9F3T3 | 438493 | features：`Pre-gelatinized` | 待裁决，明确预处理陈述尚未证实符合A；不自动放行或推断实际工艺 |
| B00838WFWM | 7608 | features：`Product Type :Mechanical Components`；title：Rye Flaked Grains | 待裁决，食用定位／机械部件字段冲突 |
| B08KSY7NYN | 441489 | features：`Grow mushrooms with ease`；description：propagate mushroom spawn、debris | 待裁决，食品用途与培养材料／清洁状态反证保留 |
| B092DF65V1 | 124908 | features：`Hulled millet is made of 100% Pure hulled millet` | 入选，成分为来源完整单粮声明；仍非真实配方独立验证 |

其余完整原文检查未发现需要改变原判定的关键反证。74条通过同一公共入口回放，62入选、4排除、8待裁决，全部对齐；自然同粮多包装、直接食用颗粒／干片、烹调及品牌描述保留正确。旧版1.1.10仍拒绝，不因为部分复核通过改报验收。

Cold Cereal／Muesli等只作为来源中的形态歧义或冲突，进入待裁决，不借类别证明实际熟制。新版本未扩展粮种、未补真实配方／供应链、不使用评论热度。最终完整扫描、独立迁移对账及最新目录样本复核仍须执行。
