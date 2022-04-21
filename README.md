# dtp-test-script

## Prerequisites

### python

需要 python >= 3.10，因为使用到了较新的语言特性

### pdm

pdm 是一个类似 npm、cargo 的 python 依赖管理工具。参见 [文档](https://pdm.fming.dev/) 进行安装。

## Usage

### 安装依赖

```shell
pdm install
```

### 格式化代码

```shell
pdm fmt
```

### 生成新的测试 trace

1. 在 `config` 中添加 json 格式的配置文件，一个文件表示一组类似的 trace
2. 在命令行执行 `pdm run gen_trace config/<config_name>.json`

配置格式如下：

```json
[
  {
    "block_num": 1000,
    "block_size": 1300,
    "block_gap": 0.001,
    "block_ddl": 200,
    "block_prio": 0,
    "trace_file_name": "trace_1300_1ms_1000.txt"
  }
]
```

目前 `block_prio` 可以配置随机生成，例子参见 [ping.json](config/ping.json)
