#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : TopGen
@Time    : 2023/12/28 16:03
@Author  : lbfeng
@File    :  primer_design.py
"""
import os
import re
import sys
import json
import time
import pandas as pd
import numpy as np
import primkit as pt
import requests
import logging
import argparse
import yaml
import datetime
from urllib.parse import urlparse

# 设置日志
logger = logging.getLogger(__name__)

# 读取配置文件
with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

# 设置命令行参数
parser = argparse.ArgumentParser(description='Your script description')
parser.add_argument('--debug', dest='debug', action='store_true',
                    help='Run in debug mode (overrides configuration file setting)')

# 解析命令行参数
args = parser.parse_args()

# 确定 DEBUG 模式：如果命令行参数指定了 --debug，则使用该参数，否则使用配置文件中的设置
DEBUG = args.debug if args.debug else config.get('DEBUG', False)

# 使用 DEBUG 变量
if DEBUG:
    # 运行调试模式下的代码
    logger.info("Running in debug mode...")
else:
    # 运行非调试模式下的代码
    logger.info("Running in normal mode...")


def emit(subject, message, attachments=None, to_addrs=None, cc_addrs=None, bcc_addrs=None):
    """
    Sends an email with the given parameters.

    :param subject: Subject of the email.
    :param message: Body of the email.
    :param attachments: List of file paths to attach to the email. Default is None.
    :param to_addrs: List of email addresses to send the email to. Default is taken from config.
    :param cc_addrs: List of email addresses for CC. Default is None.
    :param bcc_addrs: List of email addresses for BCC. Default is None.
    """
    email_manager = pt.EmailManager(config['emails']['login'], use_yagmail=True)

    default_to_addrs = config['emails']['setup']['log_toaddrs'] if DEBUG else config['emails']['setup']['qc_toaddrs']
    to_addrs = to_addrs if to_addrs is not None else default_to_addrs

    subject_prefix = '【MRD引物设计-测试】' if DEBUG else '【MRD引物设计】'
    subject = subject_prefix + subject

    email_manager.send_email(to_addrs=to_addrs, subject=subject, message=message, cc_addrs=cc_addrs,
                             bcc_addrs=bcc_addrs, attachments=attachments)


def get_sample_id(file_path):
    """
    Extracts the sample ID from a given file path which can be a URL or a file path.

    :param file_path: The source file URL or file path.
    :return: The extracted sample ID.
    """
    parsed_url = urlparse(file_path)
    file_name = os.path.basename(parsed_url.path) if parsed_url.scheme and parsed_url.netloc else os.path.basename(
        file_path)
    sampleSn = file_name.split('.')[0]
    sampleID = sampleSn[:-2]
    return sampleID


def check_sample_date(sample_id, send_email=True, email_interval=10, exit_threshold=None):
    """
    Checks the difference between the date in the sample ID and the current date.
    If the date difference exceeds the specified number of days, it sends a warning message or exits the program.

    :param sample_id: The sample ID, e.g., 'NGS231115-194WX'.
    :param send_email: Flag indicating whether to send an email.
    :param email_interval: The interval in days at which to send emails.
    :param exit_threshold: If set and the date difference exceeds this value, the program will exit.
    :return: None
    """
    # Extract the date using a regular expression
    date_match = re.search(r'NGS(\d{2})(\d{2})(\d{2})-', sample_id)
    if date_match:
        year = int(date_match.group(1)) + 2000  # Assuming '23' refers to the year 2023
        month = int(date_match.group(2))
        day = int(date_match.group(3))

        # Construct the date object
        sample_date = datetime.datetime(year, month, day)
        current_date = datetime.datetime.now()

        # Calculate the date difference
        date_difference = (current_date - sample_date).days

        # Check if the date difference exceeds the specified interval
        if exit_threshold and date_difference > exit_threshold:
            msg = f"Error: The sample {sample_id} date differs from the current date by {date_difference} days, exceeding the threshold of {exit_threshold} days. The program will exit."
            logger.critical(msg)
            if send_email:
                subject = f"样本日期检查严重警告 - {sample_id}"
                message = f"严重警告：样本ID {sample_id} 日期检查\n样本日期: {sample_date}\n当前日期: {current_date}\n日期差距: {date_difference} 天\n警告：样本日期与当前日期的差距已超过阈值 {exit_threshold} 天。\n程序将自动退出以防止进一步的数据处理。\n请立即检查相关数据并采取适当措施。"
                emit(subject, message)
            sys.exit(1)

        if date_difference > email_interval:
            msg = f"Warning: The sample {sample_id} date differs from the current date by {date_difference} days, exceeding the interval of {email_interval} days."
            logger.warning(msg)
            if send_email:
                subject = f"样本日期检查警告 - {sample_id}"
                message = f"警告：样本ID {sample_id} 日期检查\n样本日期: {sample_date}\n当前日期: {current_date}\n日期差距: {date_difference} 天\n提示：样本日期与当前日期的差距已超过设定的 {email_interval} 天。\n请检查相关数据以确保样本的有效性和时效性。"
                emit(subject, message)
        else:
            logger.info(
                f"The sample {sample_id} date differs from the current date by {date_difference} days, which does not exceed the interval of {email_interval} days.")
    else:
        logger.error("Unable to extract the date from the sample ID.")


def determine_sample_location(sampleSn):
    """
    sampleSn: sample ID
    return: NEW: 千翼CMS系统, OLD: 小阔CMS系统, NONE: CMS不存在
    """
    old_cms = config['API_CMS']['old_cms']['post_url']
    old_search = config['API_CMS']['old_search']['get_url']
    new_cms = config['API_CMS']['new_cms']['detail_url']

    old_up = config['API_CMS']['old_cms']['post_data']
    old_header = config['header']
    old_token = json.loads(requests.post(old_cms, params=old_up, headers=old_header).text)['data']['accessToken']
    old_payload = {'accessToken': old_token, "search[sampleSn][value]": sampleSn, "search[sampleSn][query]": "eq"}
    old_response = requests.get(old_search, params=old_payload, headers=old_header)
    if old_response.status_code == 200:
        old_data = json.loads(old_response.text)['data']
    else:
        logger.error('ERROR: old system response.status_code is not equal to 200.')
        sys.exit(1)

    new_payload = json.dumps({"fybh": sampleSn})
    new_header = config['API_CMS']['new_cms']['new_header']
    new_response = requests.post(new_cms, data=new_payload, headers=new_header, timeout=30)
    if new_response.status_code == 200:
        new_data = json.loads(new_response.text)
        if new_data['errorCode'] == '0' or new_data['msg'] == 'OK':
            new_data = new_data['data']
        elif new_data['errorCode'] == '400' or new_data['msg'] == '样本数据为空':
            new_data = []
        else:
            logger.error(
                'ERROR: new system errorCode is {}. errorMsg is {}.'.format(new_data['errorCode'],
                                                                            new_data['msg']))
            sys.exit(1)
    else:
        logger.logger('ERROR: new system response.status_code is not equal to 200.')
        sys.exit(1)

    return 'OLD' if old_data and not new_data else 'NEW' if new_data and not old_data else 'NONE'


def get_cms_accessToken():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'}
    postUrl = config['CMS_URL']['accessToken']['post_url']
    postData = config['CMS_URL']['accessToken']['post_data']
    try:
        response = requests.post(postUrl, params=postData, headers=headers)
        if response.status_code == 200:
            accessToken = json.loads(response.text)['data']['accessToken']
            logger.info(f'AccessToken obtained successfully, accessToken: {accessToken}')
            return accessToken
        else:
            logger.error('ERROR: response.status_code is not equal to 200.')
            sys.exit(1)
    except Exception as e:
        logger.error(f'ERROR: Error getting sample audit status of cms system. The specific reason is {e}')
        sys.exit(1)


def get_project_itemName_old(sampleSn):
    accessToken = get_cms_accessToken()
    sampleInfo_url = config['CMS_URL']['sampleInfo']['get_url']
    payload = {'accessToken': accessToken, "search[sampleSn][value]": sampleSn, "search[sampleSn][query]": "eq"}
    try:
        result = requests.get(sampleInfo_url, params=payload)
        dicts = json.loads(result.text)
        if len(dicts["data"]) > 0:
            project_id = dicts["data"][0]["itemName"]
            logger.info(f'Successfully obtained project ID, project ID: {project_id}')
            return project_id
        else:
            logger.warning('ERROR: Sample ID does not exist in cms system!')
            return 'OTHER'
    except Exception as e:
        logger.error(
            f'ERROR: An error occurred while getting the item ID of the sample for the cms system. The specific reason is {e}')
        sys.exit(1)


def get_project_type_old(sampleSn):
    project_id = get_project_itemName_old(sampleSn)
    project_id = re.search(r"^(.{7})", project_id).group(1)
    MRD_detection = config['MRD_ID']
    return "MRD" if project_id in MRD_detection else "OTHER"


def get_project_itemName(sampleSn):
    payload = {"fybh": sampleSn}
    post_data = json.dumps(payload)
    post_url = config['API_CMS']['new_cms']['detail_url']
    header = config['API_CMS']['new_cms']['new_header']
    response = requests.post(post_url, data=post_data, headers=header, timeout=30)
    if response.status_code == 200:
        sample_info = json.loads(response.text)
        if sample_info['errorCode'] == '0':
            return sample_info['data']['DD'][0]['XMMC']
        else:
            logger.error(
                'ERROR: errorCode is {}. errorMsg is {}.'.format(sample_info['errorCode'], sample_info['msg']))
            sys.exit(1)
    else:
        logger.error('ERROR: response.status_code is not equal to 200.')
        sys.exit(1)


def get_project_type(sampleSn):
    itemName = get_project_itemName(sampleSn)
    return "MRD" if '迈锐达' in itemName or 'MRD' in itemName else "OTHER"


def handle_mrd_sample(sampleID, send_email=True):
    """
    Handles the MRD sample ID by determining its project type and sending email notifications if necessary.

    :param sampleID: The MRD sample ID to be processed.
    :param send_email: Flag indicating whether to send an email.
    """
    sample_local = determine_sample_location(sampleID)
    if sample_local == 'OLD':
        project_item = get_project_type_old(sampleID)
    elif sample_local == 'NEW':
        project_item = get_project_type(sampleID)
    else:
        logger.error(
            f'ERROR: The sample {sampleID} does not exist in the small wide CMS system, nor does it exist in the thousand wing CMS system')
        sys.exit(1)

    if project_item == 'OTHER':
        logger.error(f'The sample ID {sampleID} does not belong to the MRD detection, and no primer design is required')
        if send_email:
            subject = f"样本项目检查警告 - {sampleID}"
            message = f"警告：样本ID {sampleID} 项目检查\n提示：样本不属于迈锐达检测，不进行引物设计。\n请检查样本项目配置。"
            emit(subject, message)
        sys.exit(0)


def read_loci_file(file_path):
    """
    Reads a file into a pandas DataFrame. Supports TSV, XLSX, CSV, and TXT formats with automatic delimiter detection for text files.

    :param file_path: Path to the file to be read.
    :return: A pandas DataFrame containing the file's content.
    """
    try:
        file_extension = file_path.split('.')[-1].lower()

        if file_extension in ['xlsx']:
            df = pd.read_excel(file_path).drop_duplicates()
        elif file_extension in ['csv', 'tsv', 'txt']:
            # For CSV, TSV, and TXT, try to automatically detect delimiter
            try:
                df = pd.read_csv(file_path, sep=None, engine='python').drop_duplicates()
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, sep=None, engine='python', encoding='gbk').drop_duplicates()
        else:
            logger.error(f'ERROR: Unknown file type or does not match expected file types for file: {file_path}.')
            sys.exit(1)

        return df

    except Exception as e:
        logger.error(f'ERROR: Unable to read file {file_path}, The error log is {e}.')
        sys.exit(1)


def read_hots_file():
    """
    Reads a hotspots file specified in the configuration into a pandas DataFrame.

    :return: A pandas DataFrame containing the hotspots data.
    """
    loci_hots = config['loci_hots']
    try:
        df_hots = pd.read_excel(loci_hots)
        cancer_ids = df_hots['CANCER_TYPE_ID'].unique().tolist()
        return df_hots, cancer_ids
    except Exception as e:
        logger.error(f'ERROR: Failed to retrieve the hotspots file, the specific reason is: {e}')
        sys.exit(1)


def validate_cancer_type(df_snp, cancer_id=None):
    """
    Validates if the DataFrame has 'cancer_type_ID' column or uses the provided cancer_id.

    :param df_snp: The DataFrame containing SNP loci data.
    :param cancer_id: Default cancer type ID if not present in the DataFrame.
    :return: None
    """

    def check_id(type_id):
        # 判断cancer_type_ID属于热点文件中CANCER_TYPE_ID哪个cancer tree
        return next(filter(lambda x: type_id.startswith(x), cancer_ids), type_id)

    if 'cancer_type_ID' in df_snp.columns:
        loci_cancer_id = list(set(df_snp['cancer_type_ID']))
        cancer_res_id = [check_id(k) for k in loci_cancer_id]
        if not loci_cancer_id or loci_cancer_id[0] == 'unknown':
            sampleSn = df_snp["sampleSn"].iloc[0] if "sampleSn" in df_snp.columns else "UnknownSample"
            subject = f'样本 cancer_type_ID 检查警告 - {sampleSn}'
            message = f'警告：样本ID {sample_id} 检查 cancer_type_ID 为 unknown。\n提示：样本 cancer_type_ID 为空（unknown），无法为其样本增加热点引物 。\n请检查相关数据以确保样本的准确性。'
            emit(subject, message)
    elif cancer_id:
        loci_cancer_id = [cancer_id]
        cancer_res_id = [check_id(k) for k in loci_cancer_id]
    else:
        logger.error('ERROR: "cancer_type_ID" is not in the DataFrame and no default cancer_id was provided.')
        sys.exit(1)

    return cancer_res_id


def process_hotspots(df_hots, df_loci, cancer_res_id):
    """
    Processes hotspots and loci DataFrames and merges them based on cancer research IDs.

    :param df_hots: DataFrame containing hotspots data.
    :param df_loci: DataFrame containing loci data.
    :param cancer_res_id: List of cancer research IDs.
    :return: A DataFrame with the combined and processed data.
    """
    # Filter hotspots based on cancer research IDs
    df_hot = df_hots[df_hots['CANCER_TYPE_ID'].isin(cancer_res_id)].copy().reset_index(drop=True)
    df_hot = df_hot.drop_duplicates(['primer_design_chrom', 'primer_design_start', 'primer_design_end'])

    # Select and rename specific columns
    df_hot_filt = df_hot[
        ['primer_design_chrom', 'primer_design_start', 'primer_design_end', 'Ref', 'Alt', 'Start_Position',
         'Hugo_Symbol', 'End_Position', 'pHGVS', 'cHGVS']].copy()
    df_hot_filt.rename(
        columns={'primer_design_chrom': 'chrom', 'Ref': 'ref', 'Alt': 'alt', 'primer_design_start': 'pos',
                 'Hugo_Symbol': 'gene', 'primer_design_end': 'stop'},
        inplace=True)

    # Add and format additional columns
    df_hot_filt['vaf'] = np.NaN
    df_hot_filt['chrom'] = df_hot_filt['chrom'].astype(str).apply(lambda x: 'chr' + x)
    df_hot_filt['hots'] = 1

    # Mark non-hotspots in df_loci
    df_loci['hots'] = 0

    # Combine the hotspots and loci data
    df_snp_hot = pd.concat([df_loci, df_hot_filt]).reset_index(drop=True)

    # Forward fill missing values
    df_snp_hot[['sampleSn', 'cancer_type', 'cancer_type_ID']] = df_snp_hot[
        ['sampleSn', 'cancer_type', 'cancer_type_ID']].fillna(method='ffill')

    # Fill and convert position columns
    df_snp_hot['stop'].fillna(df_snp_hot['pos'], inplace=True)
    df_snp_hot['Start_Position'].fillna(df_snp_hot['pos'], inplace=True)
    df_snp_hot['End_Position'].fillna(df_snp_hot['stop'], inplace=True)
    df_snp_hot[["stop", "Start_Position", "End_Position"]] = df_snp_hot[
        ["stop", "Start_Position", "End_Position"]].astype(int)

    df_snp_hot.reset_index(drop=True, inplace=True)

    return df_snp_hot


def loci_examined(df_loci, skip_snp_design, skip_hot_design, skip_driver_design, cancer_id=None):
    # 样本ID
    sampleSn = df_loci['sampleSn'].iloc[0] if 'sampleSn' in df_loci.columns else None

    # 查看 SNP 和 INDEL 数量，以及位点总数量
    loci_count = df_loci.shape[0]
    df_loci_snp = df_loci[(df_loci['ref'].str.len() == 1) & (df_loci['alt'].str.len() == 1)].copy()
    snp_count = df_loci_snp.shape[0]
    df_loci_indel = df_loci[(df_loci['ref'].str.len() > 1) ^ (df_loci['alt'].str.len() > 1)].copy()
    indel_count = df_loci_indel.shape[0]

    # 引物热点
    df_hots, cancer_ids = read_hots_file()
    if cancer_id and cancer_id not in cancer_ids:
        logger.error(f'ERROR: The cancer_id "{cancer_id}" is not present in the HOTS file.')
        sys.exit(1)
    cancer_res_id = validate_cancer_type(df_loci, cancer_id)

    # 开始判断
    if loci_count < 8:
        # loci < 8 (包括snp、indel)
        if skip_snp_design:
            if skip_driver_design:
                return df_loci
            elif skip_hot_design:
                return df_loci
            else:
                return process_hotspots(df_hots, df_loci, cancer_res_id)
        else:
            subject = f'样本位点数量检查警告 - {sampleSn}'
            message = f'警告：样本ID {sampleSn} 位点数量不足。\n质控结果：\nSNP位点为: {snp_count} 个，INDEL位点为: {indel_count} 个，SNP+INDEL位点数量为: {snp_count + indel_count} 。提示：当 SNP + INDEL 数量小于8，需要审核人员审核处理！\n'
            emit(subject, message)
            logging.error(f'样本ID: {sampleSn}, SNP + INDEL数量小于8, 已发邮件至审核人员处理！')
            sys.exit(0)
    elif 8 <= loci_count < 20:
        # 8 < loci < 20 + 热点
        if not skip_hot_design:
            return process_hotspots(df_hots, df_loci, cancer_res_id)
        else:
            return df_loci
    else:
        return df_loci


def execute():
    file_path = 'working/NGS231206-124WX.mrd_selected.xlsx'
    send_email = True
    email_interval = 10
    exit_threshold = 30
    skip_snp_design = False
    skip_hot_design = False
    skip_driver_design = False

    # 获取样本ID
    sampleID = get_sample_id(file_path)

    # 检查日期，默认10天发邮件提示，超过30天退出程序
    check_sample_date(sampleID, send_email=send_email, email_interval=email_interval, exit_threshold=exit_threshold)

    # 检查样本项目
    handle_mrd_sample(sampleID, send_email=send_email)

    # 读取选点文件
    df = read_loci_file(file_path)



    bed_input = "chr7\t55249070\t55249073\nchr22\t42538507\t42538510\nchr22\t42538508\t42538511\nchr7\t28996556\t28996559\nchr2\t88895350\t88895353\nchr8\t11970687\t11970690\nchr22\t42525755\t42525758\nchr7\t28995799\t28995802\nchr8\t11991448\t11991451\nchr20\t2188162\t2188165\nchr12\t52822257\t52822260\nchr17\t36636007\t36636010\nchr11\t36597312\t36597315\nchr21\t34926042\t34926045\nchr18\t28993182\t28993185\nchr3\t81698129\t81698132\nchr8\t144808746\t144808749\nchr11\t48166266\t48166269\nchr1\t231298897\t231298900\nchr9\t995918\t995921\nchr18\t995918\t995921"

    headers, cookies, token = pt.fetch_web_data(method='requests')
    post_data = pt.prepare_post_data(token, bed_input)
    down_url = pt.design_primers(post_data, method='requests', headers=headers, cookies=cookies)

    file_path = 'test.csv'
    pt.download(down_url, file_path)

    file_reader = pt.FileReader()
    df = file_reader.read_csv(file_path)
    df.insert(0, 'sampleID', len(df) * ['NGS231217-001WX'])
    db_handler = pt.DatabaseHandler('mysql+pymysql://root:root@localhost/test_db')
    table_name = 'test_table2'
    db_handler.setup_table(table_name, df.columns.to_list())

    db_handler.create_df_table(table_name, df)

    db_handler.insert_df(table_name, df)

    df = df.where(pd.notnull(df), None)
    data_dicts = df.to_dict(orient='records')
    db_handler.insert_data(table_name, data_dicts)

    engine = db_handler.get_engine()
    df.to_sql(table_name, con=engine, if_exists='append', index=False)
