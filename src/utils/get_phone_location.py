#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基于 phonenumbers (libphonenumber Python端口) 获取手机号归属地信息
"""

import sys
import phonenumbers
from phonenumbers import geocoder, carrier, timezone


def get_phone_location(phone_number, region_code=None):
    """
    获取手机号的归属地信息
    
    Args:
        phone_number: 手机号码字符串
        region_code: 国家/地区代码（可选，如 'CN' 表示中国）
    
    Returns:
        dict: 包含归属地信息的字典
    """
    try:
        # 解析手机号
        if region_code:
            parsed_number = phonenumbers.parse(phone_number, region_code)
        else:
            parsed_number = phonenumbers.parse(phone_number, None)
        
        # 验证号码是否有效
        if not phonenumbers.is_valid_number(parsed_number):
            return {
                'valid': False,
                'error': '无效的手机号码'
            }
        
        # 获取国家代码
        country_code = phonenumbers.region_code_for_number(parsed_number)
        
        # 获取归属地（地理位置）
        location_zh = geocoder.description_for_number(parsed_number, 'zh')
        location_en = geocoder.description_for_number(parsed_number, 'en')
        
        # 获取运营商信息（如果可用）
        carrier_name = None
        try:
            carrier_name = carrier.name_for_number(parsed_number, 'zh')
            if not carrier_name:
                carrier_name = carrier.name_for_number(parsed_number, 'en')
        except:
            pass
        
        # 获取时区信息
        timezones = timezone.time_zones_for_number(parsed_number)
        
        # 格式化号码
        formatted_national = phonenumbers.format_number(
            parsed_number, phonenumbers.PhoneNumberFormat.NATIONAL
        )
        formatted_international = phonenumbers.format_number(
            parsed_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL
        )
        
        return {
            'valid': True,
            'phone_number': phone_number,
            'country_code': country_code,
            'formatted_national': formatted_national,
            'formatted_international': formatted_international,
            'location_zh': location_zh if location_zh else '未知',
            'location_en': location_en if location_en else 'Unknown',
            'carrier': carrier_name if carrier_name else '未知',
            'timezones': list(timezones) if timezones else []
        }
    
    except phonenumbers.NumberParseException as e:
        return {
            'valid': False,
            'error': f'号码解析错误: {str(e)}'
        }
    except Exception as e:
        return {
            'valid': False,
            'error': f'处理错误: {str(e)}'
        }


def print_phone_info(info):
    """打印手机号归属地信息"""
    if not info['valid']:
        print(f"❌ {info.get('error', '未知错误')}")
        return
    
    print("=" * 60)
    print(f"📱 手机号码: {info['phone_number']}")
    print(f"🌍 国家/地区代码: {info['country_code']}")
    print(f"📍 归属地(中文): {info['location_zh']}")
    print(f"📍 归属地(英文): {info['location_en']}")
    print(f"📞 运营商: {info['carrier']}")
    print(f"📋 国内格式: {info['formatted_national']}")
    print(f"📋 国际格式: {info['formatted_international']}")
    if info['timezones']:
        print(f"🕐 时区: {', '.join(info['timezones'])}")
    print("=" * 60)


DEFAULT_REGION_CODE = 'CN'

def main():
    """主函数"""
    # 从命令行参数获取手机号
    if len(sys.argv) > 1:
        phone_number = sys.argv[1]
        region_code = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_REGION_CODE
    else:
        # 交互式输入
        print("请输入手机号码（支持国际格式，如 +86 13800138000 或 13800138000）:")
        phone_number = input().strip()
        print(f"请输入国家/地区代码（可选，默认值为 {DEFAULT_REGION_CODE}，如 US 表示美国，直接回车跳过）:")
        region_input = input().strip()
        region_code = region_input if region_input else DEFAULT_REGION_CODE
    
    # 获取归属地信息
    info = get_phone_location(phone_number, region_code)
    
    # 打印结果
    print_phone_info(info)


if __name__ == '__main__':
    main()

