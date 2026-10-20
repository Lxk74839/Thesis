# 本次增量TDD

- pdiag_001 RED：未知output只有普通ValueError，无安全定位；002 GREEN：本地ProtocolError仅固定stage/code/字段/索引。
- pdiag_003 RED：状态、输出形状/content、工具、JSON、角色Schema、usage分类缺失；004 GREEN，各类稳定stage/code定位，JSON只保存字符位置不保存文本。
- pdiag_005 RED：invoke仍吞成engineering_response_error；006 RED直接证明合法input_tokens由100丢为null；007 GREEN，协议错误保留具体诊断和独立解析usage。
- pdiag_008十项通过：6项新测试（多个手写PUBLIC响应分支）及4项直接受影响既有行为。包括缺失/null/无效usage仍unknown，超时保留usage和原协议诊断，工具call_id重放、strict Schema额外字段、输出cap仍拒绝；失败预算观察保留100/30，reasoning7包含在30中而非37；无usage原PUBLIC S完整发布、计量未知；最多12/最终保留及严格模式缺项拒绝有效。

测试均PUBLIC手写fixture，不是旧HTTP回放。Thesis/Job4GiB，网络、实际Key及独立标签禁止。实际provider_requests_sent=0（fixture），每个错误最多1次fixture transport且retryable=false。旧255485/240仅补充引用，不进入测试伪装旧响应。
