# Standards

Independent reviewer /root/pilot_standards. BASE05889b6, candidate85686efd88551c7201c4157e482d71be41927e82. blocking_findings: 0.

原P1已修复：t0_catalog.py:1407—1412及独立检查器757—761在输出读取/目录创建前限定当前域对应包内严格子路径；run_check.py:112—121、194—209对mkdir/rename/replace/unlink/rmdir增加路径及重解析点限制。266_output_path_green系统mkdir边界测试已通过，审查未重跑。

生产器与独立检查器均绑定十五件源码；守护补齐依赖并每250ms检测变化，发现即终止Job。268_compiler_binding_green依赖变化拒绝测试已通过。修复未引入文档标准硬违反或可行动smell；必要的独立核验重复仍有依据。

仅静态定向复审，未运行项目Python/测试/实验，未读取真实键、大对象或另一轴报告。解除程序阻塞，真实G0/G1仍须实际验证。
