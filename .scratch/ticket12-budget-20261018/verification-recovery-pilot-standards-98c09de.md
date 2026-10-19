# Standards

Reviewer: independent /root/pilot_standards. BASE05889b6, candidate98c09de187b40add76d14ea6e60b52391bf974d0. blocking_findings: 1.

[P1] 输出路径在目录创建前未受限到本包白名单。t0_catalog.py:1402—1417允许整个T0根，授权前mkdir；独立检查器756—760同样先创建父目录，run_check仅拦文件打开，无法阻止目录创建。违反AGENTS原材料只读、新产物独立路径。应在任何变更前按对应域限定package.output_roots，用系统mkdir边界零编译验证。

其余累计时间、失败记账、磁盘分域上限、程序接受绑定和检查点封存未发现确认阻塞。已检查十二项smell baseline，未发现值得单列的可行动判断；独立检查器重复有独立核验依据。仅静态审查，无项目运行、大对象或真实键读取。
