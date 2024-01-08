#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : TopGen
@Time    : 2024/1/8 15:51
@Author  : lbfeng
@File    :  get_wes_status.py
"""
import json
import logging
import requests
import argparse

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s - %(message)s')


def get_cms_accessToken():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'}
    postUrl = 'http://cms.topgen.com.cn/user/login/auth'
    postData = {'userName': 'bioinfo', 'password': 'Top50800383', 'rememberMe': '1'}
    try:
        response = requests.post(postUrl, params=postData, headers=headers)
        if response.status_code == 200:
            accessToken = json.loads(response.text)['data']['accessToken']
            logging.info(f'AccessToken obtained successfully, accessToken: {accessToken}')
            return accessToken
        else:
            logging.error('ERROR: response.status_code is not equal to 200.')
            sys.exit(1)
    except Exception as e:
        logging.error(f'ERROR: Error getting sample audit status of cms system. The specific reason is {e}')
        sys.exit(1)


def check_sample_system(sampleSn):
    """
    sampleSn: sample ID
    return: NEW: 千翼CMS系统, OLD: 小阔CMS系统, NONE: CMS不存在
    """
    old_cms = 'http://cms.topgen.com.cn/user/login/auth'
    old_search = 'http://cms.topgen.com.cn/sample/sample/search'
    new_cms = 'https://cms.hztopgen.com.cn/api/topgenApi/topgen/findSampleDetil'

    old_up = {'userName': 'bioinfo', 'password': 'Top50800383', 'rememberMe': '1'}
    old_header = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'}
    old_token = json.loads(requests.post(old_cms, params=old_up, headers=old_header).text)['data']['accessToken']
    old_payload = {'accessToken': old_token, "search[sampleSn][value]": sampleSn, "search[sampleSn][query]": "eq"}
    old_response = requests.get(old_search, params=old_payload, headers=old_header)
    if old_response.status_code == 200:
        old_data = json.loads(old_response.text)['data']
    else:
        logging.error('ERROR: old system response.status_code is not equal to 200.')
        sys.exit(1)

    new_payload = json.dumps({"fybh": sampleSn})
    new_header = {'Authorization': 'Basic TkdTTEM6VG9wZ2VuMTIz'}
    new_response = requests.post(new_cms, data=new_payload, headers=new_header, timeout=30)
    if new_response.status_code == 200:
        new_data = json.loads(new_response.text)
        if new_data['errorCode'] == '0' or new_data['msg'] == 'OK':
            new_data = new_data['data']
        elif new_data['errorCode'] == '400' or new_data['msg'] == '样本数据为空':
            new_data = []
        else:
            logging.error(
                'ERROR: new system errorCode is {}. errorMsg is {}.'.format(new_data['errorCode'],
                                                                            new_data['msg']))
            sys.exit(1)
    else:
        logging.logging('ERROR: new system response.status_code is not equal to 200.')
        sys.exit(1)

    return 'OLD' if old_data and not new_data else 'NEW' if new_data and not old_data else 'NONE'


def get_sample_status(sampleSn, sample_local):
    """
    Retrieves the status of a sample based on the specified system type.

    :param sampleSn: The sample number to check the status for.
    :param sample_local: The system type, 'OLD' or 'NEW', to determine the API to use.
    :return: The status of the sample.
    """
    if sample_local == 'NEW':
        payload = {"fybh": sampleSn}
        post_data = json.dumps(payload)
        post_url = 'https://cms.hztopgen.com.cn/api/topgenApi/topgen/findSampleDetil'
        header = {'Authorization': 'Basic TkdTTEM6VG9wZ2VuMTIz'}
        response = requests.post(post_url, data=post_data, headers=header, timeout=30)
        if response.status_code == 200:
            sample_info = json.loads(response.text)
            if sample_info['errorCode'] == '0':
                sample_status = sample_info['data']['YBFY']['YBZT']
                return sample_status
            else:
                logging.error(
                    'ERROR: errorCode is {}. errorMsg is {}.'.format(sample_info['errorCode'], sample_info['msg']))
                sys.exit(1)
        else:
            logging.error('ERROR: response.status_code is not equal to 200.')
            sys.exit(1)

    elif sample_local == 'OLD':
        access_token = get_cms_accessToken()
        sample_info_url = 'http://cms.topgen.com.cn/sample/sample/search'
        payload = {'accessToken': access_token, "search[sampleSn][value]": sampleSn, "search[sampleSn][query]": "eq"}
        try:
            result = requests.get(sample_info_url, params=payload)
            dicts = json.loads(result.text)
            if len(dicts["data"]) > 0:
                sample_status = dicts["data"][0]["sampleStatusShow"]
                logging.info(f'Successfully obtained sampleStatus, sampleStatus: {sample_status}')
                return sample_status
            else:
                logging.error('ERROR: Sample ID does not exist in cms system!')
                sys.exit(1)
        except Exception as e:
            logging.error(
                f'ERROR: An error occurred while getting the item ID of the sample for the cms system. The specific reason is {e}')
            sys.exit(1)

    else:
        logging.error(f'ERROR: Unknown system type {sample_local}')
        sys.exit(1)


def get_audit_status(sample_sn, sample_local):
    """
    Retrieves the audit status for a given sample number.

    :param sample_sn: The sample number to check the status for.
    :param sample_local: MRD sample ID system.
    :return: A tuple containing the audit status code and its description.
    """
    status_dict = {
        'YCY': '已采样',
        'YSC': '已送出',
        'YSY': '已收样',
        'JCZ': '检测中',
        'FJZ': '复检中',
        'YWC': '已完成',
        'JCZZ': '检测终止',
        'BHG': '不合格',
        'BGDSH': '报告待审核',  # 小阔接口
        'BGWTG': '报告审核未通过',  # 小阔接口
        'BGYSH': '报告已审核',  # 小阔接口
        'BYZ': '补样中',
        'ZTJC': '暂停检测',
        'DSY': '待收样',  # 千翼接口
        'YSH': '已审核',  # 千翼接口
        'WTG': '审核未通过',  # 千翼接口
        'DSH': '待审核',  # 千翼接口
        'DTJ': '待提交',  # 千翼接口
        'TYZ': '退样中',  # 千翼接口
        'YTY': '已退样',  # 千翼接口
        'YZF': '已作废',  # 千翼接口
    }

    audit_status = get_sample_status(sample_sn, sample_local)

    # Determine the status description
    if sample_local == 'OLD':
        # For the OLD system, find the abbreviation from the status description
        status_abbr = next((abbr for abbr, desc in status_dict.items() if desc == audit_status), 'Unknown')
        status_desc = audit_status
    elif sample_local == 'NEW':
        # For the NEW system, use the status abbreviation directly
        status_abbr = audit_status
        status_desc = status_dict.get(audit_status, 'Unknown Status')
    else:
        logging.error(f'ERROR: Unknown system for sample {sample_sn}.')
        sys.exit(1)

    return status_abbr, status_desc


def execute(sample_ids):
    for sample_id in sample_ids:
        # 检查样本系统（小阔或千翼）
        sample_local = check_sample_system(sample_id)

        # 检查cms样本审核状态
        status_abbr, status_desc = get_audit_status(sample_id, sample_local)

        print(f'{sample_id}\t{status_abbr}\t{status_desc}')


def main():
    parser = argparse.ArgumentParser(description='get wes check status',
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('sample_ids', nargs='+',
                        help='Sample IDs, example: NGS221109-045 NGS221110-046')

    args = parser.parse_args()

    execute(args.sample_ids)


if __name__ == '__main__':
    main()
