#! /usr/bin/bash
version="v1.1"

python3="/usr/local/Python-3.10.6/python"
primer_design="/home/ngs/PrimerDesign/script/primerDesign.py"
work_path="/home/ngs/PrimerDesign/working"
output_path="/home/ngs/PrimerDesign/primer_design"
log_path="/home/ngs/PrimerDesign/log"

filename=$(basename "${1}")
log_name=$(echo "$filename" | awk -F'W' '{print $1}')
log="$log_path/script_error_$log_name.log"
exec 3>&2 2> "$log"

if [ -f "${1}" ]; then
  mv "${1}" "$work_path/$filename"
  echo "文件 ${filename} 已被处理，请查看172.16.10.9： ${work_path} 目录" | mailx -s "【MRD引物设计-通知】${log_name} 选点文件处理通知" -r "TopGen-PD<fenglibao@topgen.com.cn>" fenglibao@topgen.com.cn
  tarp_triggered=0
  trap 'echo "primerDesign_V3.0.py 脚本发生错误，请检查日志172.16.10.9： ${log}" | mailx -a "$log" -s "【MRD引物设计-通知】${log_name} 引物设计脚本 primerDesign.py 错误" -r "TopGen-PD<fenglibao@topgen.com.cn>" fenglibao@topgen.com.cn; tarp_triggered=1' ERR
  $python3 "$primer_design" -m "sg" -i "$work_path/$filename" -o "$output_path"
  if [ $? -eq 0 ]; then
    echo "${log_name} 引物设计任务已完成，请查看172.16.10.9： ${output_path} 结果文件目录" | mailx -s "【MRD引物设计-通知】${log_name} 引物设计任务已完成" -r "TopGen-PD<fenglibao@topgen.com.cn>" fenglibao@topgen.com.cn
  else
    if [ $tarp_triggered -eq 0 ]; then
      echo "primerDesign.py 脚本发生错误，请检查日志172.16.10.9：${log}" | mailx -a "$log" -s "【MRD引物设计-通知】${log_name} 引物设计脚本 primerDesign.py 错误" -r "TopGen-PD<fenglibao@topgen.com.cn>" fenglibao@topgen.com.cn
    fi
  fi
else
  echo "${1}不是文件，跳过"
fi
