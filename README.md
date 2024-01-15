# primer-design

## 介绍
引物设计可通过守护进程或命令行工具进行，守护进程是使用systemctl + inotifywait 调用引物设计脚本，命令行工具是直接调用引物设计脚本。

## 使用说明

1.  守护进程设置参考[语雀文档](https://www.yuque.com/harley-yf9b4/loy93s/uoobzczbl1giw1hi)。
2.  命令行工具直接使用 python [primer_design.py](./primer_design.py) 调用。

## 脚本说明

1. 参数说明

```text
## 必需参数 (Required Arguments)

### 模板 (Mold)
- `-m MOLD`, `--mold MOLD`  
  Currently, the order template is only available in sh(上海百力格), hz(湖州河马), sg(上海生工), dg(上海迪赢).  
  Required: Yes  
  Choices: ['sh', 'hz', 'sg', 'dg']

### 输入文件路径 (Input File Path)
- `-i INPUT_FILE`, `--input-file INPUT_FILE`  
  Input file path for primer design.  
  Required: Yes

### 输出目录 (Output Directory)
- `-o OUTPUT_DIR`, `--output-dir OUTPUT_DIR`  
  Output directory for primer results and orders.  
  Required: Yes

## 可选参数 (Optional Arguments)

### API URL
- `--url URL`  
  URL for primer design API.  
  Default: [URL specified in config]

### 不发送邮件 (No Email)
- `--no-email`  
  Do not send email if set.  
  Action: store_false  
  Default: True

### 肿瘤标识 (Cancer ID)
- `--c-id CANCER_ID`  
  Cancer ID, if applicable.

### 邮件提醒频率 (Email Frequency)
- `--email-freq EMAIL_INTERVAL`  
  Frequency in days for sending reminder emails.  
  Type: int  
  Default: 10

### 退出时间限制 (Exit Limit)
- `--exit-lim EXIT_THRESHOLD`  
  Time limit in days to stop checking and exit.  
  Type: int  
  Default: 30

### 禁用基于时间的退出 (Disable Time-based Exit)
- `--no-timeout`  
  Disable time-based program exit.  
  Action: store_true

### 跳过SNP设计 (Skip SNP Design)
- `--skip-snp`  
  Skip SNP design if set.  
  Action: store_true

### 跳过热点设计 (Skip Hot Design)
- `--skip-hot`  
  Skip hot design if set.  
  Action: store_true

### 跳过Driver设计 (Skip Driver Design)
- `--skip-driver`
  Skip driver design if set.
  Action: store_true

### 跳过系统检查 (Skip System Check)
- `--skip-check`
  Skip system check if set.
  Action: store_true

### 跳过审核过程 (Skip Review Process)
- `--skip-review`
  Skip review process if set.
  Action: store_true

### 运行订单检查 (Run Order Check)
- `--run-order`
  Run the check_order function if set.
  Action: store_true

### 调试模式 (Debug Mode)
- `--debug`
  Run in debug mode.
  Action: store_true
```

2. config文件说明

详见 [config.yaml](./config.yaml)

4. 命令行举例

- 正常模式
```shell
python primer_design.py -m sg -i ./working/NGS231206-124WX.mrd_selected.xlsx -o ./primer_out/
```

- debug 模式
```shell
python primer_design.py -m sg --debug -i ./working/NGS231206-124WX.mrd_selected.xlsx -o ./primer_out/
```

- 跳过snp数量的判断 (预先设置snp + inhdel 数量< 8不满足质控)
```shell
 python primer_design.py -m sg -i ./working/NGS231124-168WX.mrd_selected.xlsx -o ./primer_out/ --debug --skip_snp
```

- 跳过热点引物设计 (若选点文件中无cancer_type_ID列或是不需要热点引物设计，则使用该参数)
```shell
python primer_design.py -m sg -i ./working/NGS231124-168WX.mrd_selected.xlsx -o ./primer_out/ --debug --skip_hot
```

- 当然也可以使用 --cancer_id 增加热点，详见[热点数据库](./order_template/pancancer_hotspot_mutation.xlsx)
```shell
python primer_design.py -m sg -i ./working/NGS231124-168WX.mrd_selected.xlsx -o ./primer_out/ --cancer_id TS01
```

- 跳过driver优先设计 (若选点文件中无driver_gene列或是不需要driver优先设计，则使用该参数)
```shell
python primer_design.py -m sg -i ./working/NGS231124-168WX.mrd_selected.xlsx -o ./primer_out/ --debug --skip_driver
```

- 若只测试引物设计情况，可选择以下方案设计并查看(首先测试的位点文件必须包含 `sampleSn chrom pos ref alt` 这5列数据)，如果想使用`chrom pos`2列设计的话，详见 [primkit](https://github.com/Enthusiasm23/primkit) 。
```shell
python primer_design.py -m sg -i ./working/NGS231124-168WX.mrd_selected.xlsx -o ./primer_out/ --debug --skip_hot --skip_driver --skip_snp --skip_check --skip_review
```

- 跳过样本时间检测（即默认的10天邮件警告，30天退出引物设计程序）
```shell
python primer_design.py -m sg -i ./working/NGS231124-168WX.mrd_selected.xlsx -o ./primer_out/ --no-timeout
```

- 运行订单发送检测（默认不运行订单发送）
```shell
python primer_design.py -m sg -i ./working/NGS231124-168WX.mrd_selected.xlsx -o ./primer_out/ --run-order
```

- 更多参数使用
```shell
python primer_design.py -h
```

## 数据库说明

数据库为 172.16.10.55 ngs

- **mrd_selection**

    存储处理*mrd.selected.tsv文件后的数据，包括删除位点，增加位点，添加热点等处理。

- **mfe_primers**

    存储引物设计过程的数据

- **primer_combined**

    存储引物设计最终结果与被选中位点附带其他信息的合并数据

- **primer_order**

    存储订单表数据

- **monitor_order**

    存储检测引物订购单是否发送，以及样本审核状态

## 其余脚本说明

1. **get_wes_status.py** - 获取CMS中样本的审核状态

```shell
python get_wes_status.py sample_id1 sample_id2 ...
```

## 注意：
建议使用命令行工具嵌入pipeline中运行，守护进程程序暂未测试和使用。
