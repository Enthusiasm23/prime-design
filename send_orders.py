#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : TopGen
@Time    : 2024/1/17 14:51
@Author  : lbfeng
@File    : send_orders.py
"""
import os
import sys
import argparse
import logging
import yaml
import primkit as pt
from primer_design import emit, check_email_sent, get_audit_status, update_email_status

logger = logging.getLogger(__name__)

with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.load(f, Loader=yaml.FullLoader)


def check_order(sampleID, primer_result, debug):
    """
    Monitors and manages the process of checking sample audit status, sending emails, and updating database.

    :param sampleID: The unique identifier for the sample.
    :param primer_result: The file path of the primer result that will be attached to the email.
    :param debug: A boolean flag to enable debug mode.
    """
    email_manager = pt.EmailManager(config['emails']['login'], use_yagmail=True)
    subject_prefix = '【MRD引物设计-测试】' if debug else '【MRD引物设计】'

    test_toaddrs = config['emails']['setup']['log_toaddrs']
    qc_toaddrs = config['emails']['setup']['qc_toaddrs']
    order_toaddrs = config['emails']['setup']['order_toaddrs']
    order_cc = config['emails']['setup']['cc']
    test_cc = config['emails']['setup']['log_cc']

    toaddrs = test_toaddrs if DEBUG else order_toaddrs
    cc = test_cc if DEBUG else order_cc

    subject = f'样本引物合成订购 (自动发送) - {sampleID} '
    message = f'样本ID：{sampleID}\nCMS审核结果：已通过\n引物结果：{os.path.basename(primer_result)}（见附件）'

    email_status = check_email_sent(sampleID, 'monitor_order')

    if email_status == 0:
        status_abbr, status_desc = get_audit_status(sampleID)
        review_status = f'{status_abbr}({status_desc})'

        # 审核通过
        if status_abbr in ['YWC', 'YSH', 'BGYSH']:
            email_manager.send_email(to_addrs=toaddrs, subject=subject_prefix + subject, message=message, cc_addrs=cc, attachments=[primer_result])
            update_email_status(sampleID, 'monitor_order', review_status=review_status, email_sent=0 if DEBUG else 1)
            logger.info('Primer design order has been sent.')
            sys.exit(0)

        # 检测中
        elif status_abbr in ['JCZ', 'DSH', 'BGDSH']:
            subject = f'样本审核状态持续检测 - {sampleID}'
            message = f'样本ID {sampleID} 审核状态持续检测中···\n目前样本审核状态：{review_status}。\n请检查样本审核状态并进行更新。'
            email_manager.send_email(to_addrs=qc_toaddrs, subject=subject_prefix + subject, message=message, attachments=[primer_result])
            logger.error('Primer order review status not updated, waiting for CMS review status update...')
            sys.exit(1)

        # 检测终止
        else:
            subject = f'样本状态检测异常警告 - {sampleID}'
            message = f'警告：样本ID {sampleID} 样本状态检测异常。\nCMS审核状态：{review_status}\n请检查相关数据并采取适当措施。'
            email_manager.send_email(to_addrs=qc_toaddrs, subject=subject_prefix + subject, message=message)
            update_email_status(sampleID, 'monitor_order', review_status=review_status,
                                email_sent=2)
            logger.error(
                f'Sample ID {sampleID} Detect the anomaly and exit the program.')
            sys.exit(1)

    elif email_status in [1, 2]:
        # 如果EmailSent是1，已经发送过邮件了，如果DEBUG为True还会发送至测试邮箱
        # 如果EmailSent是2，不发送邮件，项目终止了
        if email_status == 1 and debug:
            email_manager.send_email(to_addrs=test_toaddrs, subject=subject_prefix + subject, message=message, attachments=[primer_result])
            logger.info(f"Email sent to DEBUG addresses for SampleID: {sampleID}.")

        logger.info(f"No action needed for SampleID: {sampleID} as EmailSent is {email_status}")
        sys.exit(0)

    else:
        # 如果EmailSent是None或其他值，发送错误消息并退出程序
        logger.error(f"Unexpected EmailSent status for SampleID: {sampleID}")
        sys.exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Automatic primer design.')
    parser.add_argument('-s', '--sample-id', required=True, dest='sampleID',
                        help='Sample ID for primer design.')
    parser.add_argument('-p', '--primer-result', required=True, dest='primer_result',
                        help='result for primer design.')
    parser.add_argument('--debug', action='store_true', dest='debug',
                        help='Run in debug mode.')
    args = parser.parse_args()
    DEBUG = args.debug if args.debug else config.get('DEBUG', False)
    check_order(args.sampleID, args.primer_result, DEBUG)
