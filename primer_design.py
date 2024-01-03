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
import primkit
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


def validate_cancer_type(df_snp, hots_cancer_ids, cancer_id=None):
    """
    Validates if the DataFrame has 'cancer_type_ID' column or uses the provided cancer_id.

    :param df_snp: The DataFrame containing SNP loci data.
    :param hots_cancer_ids: cancer type ID of hotspot file
    :param cancer_id: Default cancer type ID if not present in the DataFrame.
    :return: None
    """

    def check_id(type_id):
        # 判断cancer_type_ID属于热点文件中CANCER_TYPE_ID哪个cancer tree
        return next(filter(lambda x: type_id.startswith(x), hots_cancer_ids), type_id)

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

    # Filter hotspots based on cancer research IDs and remove duplicates
    df_hot = df_hots[df_hots['CANCER_TYPE_ID'].isin(cancer_res_id)].drop_duplicates(
        ['primer_design_chrom', 'primer_design_start', 'primer_design_end'])

    # Prepare df_hot for merging
    df_hot = df_hot.rename(columns={
        'primer_design_chrom': 'chrom',
        'primer_design_start': 'pos',
        'primer_design_end': 'stop',
        'Ref': 'ref',
        'Alt': 'alt',
        'Hugo_Symbol': 'gene'
    })
    df_hot = df_hot.assign(vaf=np.NaN, hots=1)
    df_hot['chrom'] = df_hot['chrom'].astype(str).apply(lambda x: 'chr' + x)

    # Select relevant columns for merging
    columns = ['chrom', 'pos', 'stop', 'ref', 'alt', 'Start_Position', 'End_Position', 'pHGVS', 'cHGVS', 'gene', 'vaf',
               'hots']
    df_hot = df_hot[columns]

    # Mark non-hotspots in df_loci
    df_loci = df_loci.assign(hots=0)

    # Combine the hotspots and loci data
    df_combined = pd.concat([df_loci, df_hot], ignore_index=True)

    # Fill missing values and adjust data types
    df_combined['stop'].fillna(df_combined['pos'], inplace=True)
    df_combined['Start_Position'].fillna(df_combined['pos'], inplace=True)
    df_combined['End_Position'].fillna(df_combined['stop'], inplace=True)
    df_combined[['stop', 'Start_Position', 'End_Position']] = df_combined[
        ['stop', 'Start_Position', 'End_Position']].astype(int)

    # Forward fill missing values for certain columns
    fill_columns = ['sampleSn', 'cancer_type', 'cancer_type_ID']
    df_combined[fill_columns] = df_combined[fill_columns].fillna(method='ffill')

    return df_combined


def loci_examined(df_loci, skip_snp_design, skip_hot_design, skip_driver_design, cancer_id=None, send_email=True):
    """
    Examines loci in a given DataFrame and performs various checks and processes based on the parameters provided.

    :param df_loci: DataFrame containing loci information.
    :param skip_snp_design: Boolean flag to skip SNP design.
    :param skip_hot_design: Boolean flag to skip hot design.
    :param skip_driver_design: Boolean flag to skip driver design.
    :param cancer_id: Optional cancer ID for further analysis.
    :param send_email: Flag indicating whether to send an email.

    :return: Processed DataFrame based on the given parameters and conditions.
    """

    # Sample ID
    sampleSn = df_loci['sampleSn'].iloc[0] if 'sampleSn' in df_loci.columns else None

    # Count SNP and INDEL and total loci
    loci_count = df_loci.shape[0]
    df_loci_snp = df_loci[(df_loci['ref'].str.len() == 1) & (df_loci['alt'].str.len() == 1)].copy()
    snp_count = df_loci_snp.shape[0]
    df_loci_indel = df_loci[(df_loci['ref'].str.len() > 1) ^ (df_loci['alt'].str.len() > 1)].copy()
    indel_count = df_loci_indel.shape[0]

    # 仅当 loci_count 小于 20 时读取热点信息
    def process_hotspots_logic():
        df_hots, cancer_ids = read_hots_file()
        if cancer_id and cancer_id not in cancer_ids:
            logger.error(f'ERROR: The cancer_id "{cancer_id}" is not present in the HOTS file.')
            sys.exit(1)
        cancer_res_id = validate_cancer_type(df_loci, cancer_ids, cancer_id)
        return process_hotspots(df_hots, df_loci, cancer_res_id)

    # Decision-making
    if loci_count < 8:
        if skip_snp_design:
            if not (skip_driver_design or skip_hot_design):
                return process_hotspots_logic()
            return df_loci
        else:
            logging.error(f'样本ID: {sampleSn}, SNP + INDEL数量小于8, 已发邮件至审核人员处理！')
            if send_email:
                subject = f'样本位点数量检查警告 - {sampleSn}'
                message = f'警告：样本ID {sampleSn} 位点数量不足。\n质控结果：SNP位点为: {snp_count} 个，INDEL位点为: {indel_count} 个，SNP+INDEL位点数量为: {snp_count + indel_count} 。\n提示：当 SNP + INDEL 数量小于8，需要审核人员审核处理！\n'
                emit(subject, message)
            sys.exit(0)
    elif 8 <= loci_count < 20:
        if not skip_hot_design:
            return process_hotspots_logic()
    return df_loci


def add_templateID(df_loci):
    """
    Processes a DataFrame of genetic loci to add a TemplateID based on chromosome position and type (SNP, INDEL, hotspot).

    :param df_loci: DataFrame containing loci information.
    :return: DataFrame with added TemplateID and adjusted positions.
    """
    # Drop duplicates and make a copy
    df_dup = df_loci.drop_duplicates().copy()

    # Check if there are INDELs
    has_indel = (df_dup['ref'].str.len() > 1).any() or (df_dup['alt'].str.len() > 1).any()

    # Adjust 'stop' and 'pos' based on the presence of 'stop' column and INDELs
    if 'stop' in df_dup.columns:
        df_dup['stop'] += 1
        df_dup['pos'] -= 1
    else:
        if has_indel:
            df_dup['stop'] = df_dup.apply(lambda row: row['pos'] + max(len(row['ref']), len(row['alt'])), axis=1)
        else:
            df_dup['stop'] = df_dup['pos'] + 1
        df_dup['pos'] -= 1

    # Create TemplateID
    df_dup['TemplateID'] = df_dup['chrom'] + ':' + df_dup['pos'].astype(str) + '-' + df_dup['stop'].astype(str)

    # Drop duplicates based on TemplateID
    df_dup.drop_duplicates('TemplateID', inplace=True)

    return df_dup


def select_site(df_source, df_res=None, not_used=None, num=20, driver=None):
    """
    Selects sites from a source DataFrame and handles unused and driver sites.

    :param df_source: DataFrame containing source data.
    :param df_res: DataFrame containing results data.
    :param not_used: List of TemplateIDs not used.
    :param num: Number of sites to select.
    :param driver: List of driver TemplateIDs.
    :return: A string of selected site information and a list of not used TemplateIDs.
    """

    def convert_row_to_string(row):
        row_string = "\t".join(str(x) for x in row)
        return row_string + "\n"

    # Function to handle selection and conversion of data
    def handle_selection(df, number):
        selected = df.head(number).copy()
        used_ids = selected['TemplateID'].to_list()
        unused_ids = df[~df['TemplateID'].isin(used_ids)]['TemplateID'].to_list()
        result_str = "".join(selected[['chrom', 'pos', 'stop']].apply(convert_row_to_string, axis=1))[:-1]
        return result_str, unused_ids

    if df_res is None and not_used is None:
        return handle_selection(df_source, num)
    else:
        df_filt = df_res if driver is None else df_res[~df_res['TemplateID'].isin(driver)]
        # Combine successfully used and not used
        all_used = df_filt['TemplateID'].to_list() + (not_used or [])
        df_filtered = df_source[df_source['TemplateID'].isin(all_used)].drop_duplicates('TemplateID', keep='first')

        return handle_selection(df_filtered, num)


def design_primers_core(url, outcome_dir, sampleID, result_string, file_suffix='driver'):
    """
    Core function for primer design. It selects sites, fetches web data, prepares and posts data for primer design,
    downloads the results, and reads the resulting data.

    :param url: URL for the web service for primer design.
    :param outcome_dir: Directory to save the outcome files.
    :param sampleID: Sample ID for the primer design.
    :param result_string: Format string for primer design.
    :param file_suffix: Suffix for the file name.
    :return: DataFrame containing the results of primer design.
    """

    # Ensure the sampleID directory exists
    sample_dir = os.path.join(outcome_dir, sampleID)
    if not os.path.exists(sample_dir):
        os.makedirs(sample_dir)

    # Select sites and prepare data for posting
    headers, cookies, token = primkit.fetch_web_data(url=url, method='requests')
    post_data = primkit.prepare_post_data(token, result_string)

    # Design primers and download the results
    down_url = primkit.design_primers(post_data, method='requests', headers=headers, cookies=cookies)
    save_path = os.path.join(sample_dir, f'{sampleID}-{file_suffix}.csv')
    primkit.download(down_url, save_path)

    # Read and log the result
    file_reader = primkit.FileReader()
    df_res = file_reader.read_csv(save_path)

    # Add a column to distinguish file_suffix results
    df_res['Suffix'] = file_suffix

    logger.info(f'第 {file_suffix} 次引物设计结果为:\n{df_res}')

    return df_res, save_path


def save_to_database(df_res, table_name=None):
    """
    Saves the given DataFrame to a database table specified in the configuration or the provided table name.

    :param df_res: DataFrame to be saved in the database.
    :param table_name: Optional. The name of the table where the DataFrame will be saved. If not provided, will use default from config.
    """

    global config  # Assuming config is a global variable

    db_config = config['DB_CONFIG']
    db_url = f"mysql+pymysql://{db_config['user']}:{db_config['passwd']}@{db_config['host']}:{db_config['port']}/{db_config['db']}"

    # Use the provided table_name or default to the one in config
    if table_name is None:
        table_name = db_config.get('table', 'default_table')

    db_handler = primkit.DatabaseHandler(db_url)
    db_handler.create_df_table(table_name, df_res)
    db_handler.insert_df(table_name, df_res)


def first_check_driver(df_driver, url, outcome_dir, sampleID):
    """
    Checks the number of driver genes in the given DataFrame and performs actions accordingly.

    :param df_driver: DataFrame containing driver gene information.
    :param url: URL for the web service for primer design.
    :param outcome_dir: Directory to save the outcome files.
    :param sampleID: Sample ID for the driver check.
    :return: List of TemplateIDs or None.
    """
    driver_count = df_driver.shape[0]

    if driver_count == 0:
        logger.info(f'提示：样本ID {sampleID} 选点文件中无driver基因。')
        return None

    if driver_count == 1:
        logger.info(f'提示：样本ID {sampleID} 选点文件中driver基因数量为1，无需进行单独引物设计。')
        return df_driver['TemplateID'].to_list()

    logger.info(f'提示：样本ID {sampleID} 选点文件中driver基因数量为{driver_count}，进行单独引物设计测试排除兼容性。')

    result_string, not_used = select_site(df_driver)
    df_res, save_path = design_primers_core(url, outcome_dir, sampleID, result_string, file_suffix='driver')

    # Save the DataFrame to a table in the database.
    save_to_database(df_res, table_name='test_primers')

    return df_res['TemplateID'].to_list()


def process_driver(df_loci, url, outcome_dir, sampleID, skip_driver_design):
    """
    Process the provided DataFrame to filter out driver genes, calculate the number of designs needed,
    and generate a list of driver genes.

    :param df_loci: DataFrame containing loci information.
    :param url: URL used in first_check_driver function.
    :param outcome_dir: Parameter used in first_check_driver function.
    :param sampleID: Sample ID used in first_check_driver function.
    :param skip_driver_design: Boolean flag to indicate if driver is to be considered.
    :return: Tuple containing DataFrame without driver genes, number of designs needed, and list of driver genes.
    """

    def convert_driver_to_string(lst):
        return ''.join(
            [f"{item.split(':')[0]}\t{item.split(':')[1].split('-')[0]}\t{item.split(':')[1].split('-')[1]}\n" for item
             in lst])

    if skip_driver_design or df_loci['driver'].sum() == 0:
        return df_loci, 20, [], ''

    driver_list = first_check_driver(df_loci[df_loci['driver'] == 1], url, outcome_dir, sampleID)
    driver_str = convert_driver_to_string(driver_list)

    df_no_driver = df_loci[~(df_loci['driver'] == 1)]
    design_num = max(20 - len(driver_list), 0)

    return df_no_driver, design_num, driver_list, driver_str


def update_primer_design(df_res, driver_list, design_num):
    """
    Updates the number of designs needed and driver list based on the current results.

    :param df_res: DataFrame with the current primer design results.
    :param driver_list: List of driver gene TemplateIDs.
    :param design_num: Initial number of designs needed.
    :return: Tuple of updated number of designs needed and updated driver list.
    """
    current_drivers = df_res[df_res['TemplateID'].isin(driver_list)]['TemplateID'].to_list()
    updated_design_num = design_num + len(driver_list) - len(current_drivers)

    return updated_design_num, current_drivers


def select_site_logic(df_no_driver, df_res, not_used, design_num, driver_list, driver_str, num):
    """
    Logic for selecting sites for primer design.
    """
    if num == 1:
        result_string, not_used = select_site(df_no_driver, num=design_num)
        primer_string = driver_str + result_string if driver_str else result_string
    else:
        new_design_num, new_driver_list = update_primer_design(df_res, driver_list, design_num)
        result_string, not_used = select_site(df_no_driver, df_res, not_used, num=new_design_num, driver=new_driver_list)
        primer_string = driver_str + result_string if driver_str else result_string

    return primer_string, not_used


def should_exit_loop(df_res, not_used):
    """
    Determine if the loop should exit based on the results.

    :param df_res: DataFrame with the current primer design results.
    :param not_used: List of TemplateIDs not used in the current primer design.
    :return: Boolean indicating whether to exit the loop.
    """
    if df_res.shape[0] == 20 or not not_used or len(not_used) == 0:
        return True
    return False


def perform_primer_design(df_no_driver, sampleID, url, outcome_dir, design_num, driver_list, driver_str):
    """
    Perform primer design based on the given data.
    """
    num = 0
    df_res = pd.DataFrame()
    not_used = []

    while True:
        num += 1
        logger.info(f'样本 - {sampleID} 第 {num} 次引物设计')

        # Select sites for primer design
        result_string, not_used = select_site_logic(df_no_driver, df_res, not_used, design_num, driver_list, driver_str, num)

        # Design primers and process results
        df_res, save_path = design_primers_core(url, outcome_dir, sampleID, result_string, file_suffix=num)

        # Save the DataFrame to a table in the database.
        save_to_database(df_res, table_name='test_primers')

        if should_exit_loop(df_res, not_used):
            break

    return df_res


def execute():
    file_path = 'working/NGS231206-124WX.mrd_selected.xlsx'
    send_email = False
    email_interval = 10
    exit_threshold = 30
    skip_snp_design = False
    skip_hot_design = False
    skip_driver_design = False
    cancer_id = None
    url = config['mfe_primer']
    out_dir = 'primer_out'
    outcome_dir = os.path.join(os.path.abspath(out_dir), 'primer_outcome')
    order_dir = os.path.join(os.path.abspath(out_dir), 'primer_order')

    # 获取样本ID
    sampleID = get_sample_id(file_path)

    # 检查日期，默认10天发邮件提示，超过30天退出程序
    check_sample_date(sampleID, send_email=send_email, email_interval=email_interval, exit_threshold=exit_threshold)

    # 检查样本项目
    handle_mrd_sample(sampleID, send_email=send_email)

    # 读取选点文件
    df = read_loci_file(file_path)

    # 判断和处理选点
    df_loci = loci_examined(df, skip_snp_design, skip_hot_design, skip_driver_design, cancer_id=cancer_id,
                            send_email=send_email)

    # 添加 templateID
    df_design = add_templateID(df_loci)

    # 优先 driver 基因进行引物设计
    df_no_driver, design_num, driver_list, driver_str = process_driver(df_design, url, outcome_dir, sampleID, skip_driver_design)

    # 循环设计引物
    df_res = perform_primer_design(df_no_driver, sampleID, url, outcome_dir, design_num, driver_list, driver_str)


