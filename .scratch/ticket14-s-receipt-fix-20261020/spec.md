# S执行回执定向修正（用户确认）

BASE896d3b8，仅修回执冲突。旧.scratch/ticket14-s-engineering-20261020/result.json保留原字节；实际执行统一写execution-result.json。公共测试接口为run_once.ensure_first_execution(package, attempt_path)，仅临时PUBLIC文件：旧not_started不阻止首次准备；claim、真实receipt、实际attempt及execution-resources任一存在均拒绝。启动父进程及执行子进程均复用该检查；实际claim仍exclusive创建。

Windows worker及真实离线回归/双轴审查复用，不修改不重测。S完整流程/1493非执行预检/R验收复用。只对回执增量RED/GREEN并固定同一candidate双轴复核。通过后核对原未消耗S许可，执行一次；所有原12生成/0count/0other/无重试、输出/正文/时间/存储/最终提交预留条件不变。

离线总上限更新1980秒，继承1838.5422038；历史1800秒超限保留。新修正包120秒含测试/审查/归档，预留15秒，写64MiB/内存4GiB。native20秒及16MiB保守计费含所有非测试非代理操作与收尾，不称实测。原S360秒另域记录，不挪用。
