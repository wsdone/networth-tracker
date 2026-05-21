"""Bill parsers for WeChat, Douyin, and Alipay exports."""
import logging
import re
import subprocess
import tempfile
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def parse_wechat_xlsx(filepath: str) -> list[dict]:
    """Parse WeChat payment bill (xlsx)."""
    import openpyxl

    wb = openpyxl.load_workbook(filepath, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    # Find header row (contains '交易时间')
    header_idx = None
    for i, row in enumerate(rows):
        if row and any(str(c) == '交易时间' for c in row if c):
            header_idx = i
            break
    if header_idx is None:
        return []

    headers = [str(c) if c else '' for c in rows[header_idx]]
    col_map = {}
    for j, h in enumerate(headers):
        if '交易时间' in h:
            col_map['time'] = j
        elif '交易对方' in h:
            col_map['counterpart'] = j
        elif '商品' in h:
            col_map['product'] = j
        elif '收/支' in h:
            col_map['direction'] = j
        elif '金额' in h:
            col_map['amount'] = j
        elif '支付方式' in h:
            col_map['pay_method'] = j
        elif '当前状态' in h:
            col_map['status'] = j
        elif '交易单号' in h:
            col_map['tx_id'] = j
        elif '备注' in h:
            col_map['remark'] = j

    result = []
    for row in rows[header_idx + 1:]:
        if not row or not row[col_map.get('time', 0)]:
            continue
        try:
            direction = str(row[col_map.get('direction', -1)] or '')
            status = str(row[col_map.get('status', -1)] or '')
            is_refund = '退款' in status

            if direction == '支出' and not is_refund:
                record_direction = 'expense'
                if status not in ('支付成功', '已转账'):
                    continue
            elif is_refund:
                record_direction = 'income'
                if status != '退款成功':
                    continue
            elif direction == '收入':
                record_direction = 'income'
                if '成功' not in status:
                    continue
            else:
                continue

            time_val = row[col_map['time']]
            if isinstance(time_val, datetime):
                tx_date = time_val.date()
            else:
                tx_date = date.fromisoformat(str(time_val)[:10])
            amount_raw = row[col_map['amount']]
            amount = abs(float(str(amount_raw).replace('¥', '').replace(',', '').strip()))
            tx_id = str(row[col_map.get('tx_id', -1)] or '').strip()
            counterpart = str(row[col_map.get('counterpart', -1)] or '').strip()
            product = str(row[col_map.get('product', -1)] or '').strip()
            pay_method = str(row[col_map.get('pay_method', -1)] or '').strip()
            remark = str(row[col_map.get('remark', -1)] or '').strip()
            notes = counterpart
            if product and product != '/' and product != 'GOODS':
                notes += f' - {product}'
            if remark and remark != '/':
                notes += f' ({remark})'
            category = '退款' if is_refund else _guess_category(counterpart, product)
            if is_refund:
                notes = f'退款 - {counterpart}'
            result.append({
                'date': tx_date,
                'amount': amount,
                'category': category,
                'direction': record_direction,
                'notes': notes.strip(' -()') or counterpart,
                'pay_method': pay_method,
                'external_id': tx_id,
                'source': 'wechat',
            })
        except Exception as e:
            logger.warning(f"WeChat parse row error: {e}")
    return result


def parse_douyin_pdf(filepath: str) -> list[dict]:
    """Parse Douyin payment bill (PDF)."""
    try:
        result = subprocess.run(
            ['pdftotext', '-layout', filepath, '-'],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            logger.error(f"pdftotext failed: {result.stderr}")
            return []
        text = result.stdout
    except FileNotFoundError:
        logger.error("pdftotext not installed")
        return []

    lines = text.split('\n')
    records = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Match date pattern at start of line: 2026-05-18 16:13:44
        m = re.match(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(收入|支出|其他)\s+([\d.]+)\s+(.*)', line)
        if m:
            tx_time = m.group(1)
            direction = m.group(2)
            amount = float(m.group(3))
            rest = m.group(4).strip()
            # Next line may have continuation of pay method
            pay_method = rest
            tx_id = ''
            counterpart = ''
            # Try to extract from current + next line
            # Pattern: pay_method   tx_id   counterpart   merchant_id
            # Sometimes pay method wraps to next line
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                # If next line starts with digits (continuation of pay method like card number)
                if next_line and not re.match(r'\d{4}-\d{2}-\d{2}', next_line) and not next_line.startswith('说明'):
                    pay_method += next_line
                    i += 1

            # Parse pay_method field which now contains: method  tx_id  counterpart  merchant_id
            # Extract using known patterns
            parts = re.split(r'\s{2,}', pay_method)
            if len(parts) >= 3:
                pay_method_clean = parts[0].strip()
                tx_id = parts[1].strip()
                counterpart = parts[2].strip() if len(parts) > 2 else ''
            else:
                pay_method_clean = pay_method

            # Clean up pay method - remove card number wrapping
            pay_method_clean = re.sub(r'\s+', '', pay_method_clean)

            if direction == '支出' and tx_id:
                records.append({
                    'date': date.fromisoformat(tx_time[:10]),
                    'amount': amount,
                    'category': _guess_category(counterpart, ''),
                    'direction': 'expense',
                    'notes': counterpart or '抖音消费',
                    'pay_method': pay_method_clean,
                    'external_id': tx_id,
                    'source': 'douyin',
                })
            elif direction == '收入' and tx_id:
                records.append({
                    'date': date.fromisoformat(tx_time[:10]),
                    'amount': amount,
                    'category': '退款' if '退款' in counterpart else '其他',
                    'direction': 'income',
                    'notes': counterpart or '抖音收入',
                    'pay_method': pay_method_clean,
                    'external_id': tx_id,
                    'source': 'douyin',
                })
        i += 1
    return records


def parse_alipay_csv(filepath: str) -> list[dict]:
    """Parse Alipay bill (CSV, GBK encoded)."""
    # Try GBK first, then UTF-8
    for encoding in ('gbk', 'utf-8-sig', 'utf-8'):
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                lines = f.readlines()
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    else:
        return []

    # Find header row
    header_idx = None
    for i, line in enumerate(lines):
        if '交易时间' in line and '收/支' in line:
            header_idx = i
            break
    if header_idx is None:
        return []

    headers = [h.strip() for h in lines[header_idx].split(',')]
    col_map = {}
    for j, h in enumerate(headers):
        if '交易时间' in h:
            col_map['time'] = j
        elif '交易对方' in h:
            col_map['counterpart'] = j
        elif '商品说明' in h:
            col_map['product'] = j
        elif '收/支' in h:
            col_map['direction'] = j
        elif h == '金额':
            col_map['amount'] = j
        elif '收/付款方式' in h:
            col_map['pay_method'] = j
        elif '交易状态' in h:
            col_map['status'] = j
        elif '交易订单号' in h:
            col_map['tx_id'] = j
        elif '交易分类' in h:
            col_map['category'] = j
        elif '备注' in h:
            col_map['remark'] = j

    result = []
    for line in lines[header_idx + 1:]:
        line = line.strip()
        if not line or line.startswith('-'):
            continue
        parts = [p.strip() for p in line.split(',')]
        if len(parts) < 8:
            continue
        try:
            direction = parts[col_map.get('direction', -1)] if col_map.get('direction', -1) < len(parts) else ''
            status = parts[col_map.get('status', -1)] if col_map.get('status', -1) < len(parts) else ''
            counterpart = parts[col_map.get('counterpart', -1)] if col_map.get('counterpart', -1) < len(parts) else ''
            product = parts[col_map.get('product', -1)] if col_map.get('product', -1) < len(parts) else ''

            # Handle refunds (不计收支 + 退款 in product)
            is_refund = '退款' in status or '退款' in product or '退款' in counterpart
            if direction == '支出' and not is_refund:
                record_direction = 'expense'
            elif is_refund:
                record_direction = 'income'
            elif direction == '收入':
                record_direction = 'income'
            else:
                continue

            if '成功' not in status:
                continue
            time_str = parts[col_map['time']]
            tx_date = date.fromisoformat(time_str[:10])
            amount_raw = parts[col_map['amount']]
            amount = abs(float(amount_raw.replace('¥', '').replace(',', '').strip()))
            if amount <= 0:
                continue
            pay_method = parts[col_map.get('pay_method', -1)] if col_map.get('pay_method', -1) < len(parts) else ''
            tx_id = parts[col_map.get('tx_id', -1)].strip('\t ') if col_map.get('tx_id', -1) < len(parts) else ''
            alipay_category = parts[col_map.get('category', -1)] if col_map.get('category', -1) < len(parts) else ''
            notes = counterpart
            if product and product != '/':
                notes += f' - {product}'

            if is_refund:
                category = '退款'
                notes = f'退款 - {notes.strip(" -")}'
            else:
                category = _map_alipay_category(alipay_category) or _guess_category(counterpart, product)

            result.append({
                'date': tx_date,
                'amount': amount,
                'category': category,
                'direction': record_direction,
                'notes': notes.strip(' -') or counterpart or '支付宝消费',
                'pay_method': pay_method,
                'external_id': tx_id,
                'source': 'alipay',
            })
        except Exception as e:
            logger.warning(f"Alipay parse row error: {e}")
    return result


def _map_alipay_category(cat: str) -> str | None:
    """Map Alipay's built-in category to our categories."""
    mapping = {
        '餐饮美食': '餐饮',
        '交通出行': '交通',
        '日用百货': '购物',
        '充值缴费': '其他',
        '休闲娱乐': '娱乐',
        '医疗健康': '医疗',
        '教育学习': '教育',
    }
    return mapping.get(cat)


def _guess_category(counterpart: str, product: str) -> str:
    """Guess expense category from counterpart and product names."""
    text = f'{counterpart} {product}'.lower()
    # Specific keywords first (before broad ones like 美团)
    if any(k in text for k in ['充电宝']):
        return '其他'
    if any(k in text for k in ['超市', '便利店', '商店', 'mall', '购物', '商场', '赵一鸣', '拼多多']):
        return '购物'
    if any(k in text for k in ['餐', '饭', '面', '火锅', '烧烤', '奶茶', 'coffee', '咖啡', 'luckin', '麦当劳', 'kfc', '肯德基', '外卖', '美团', '饿了么', '食品', '零食', '饮料']):
        return '餐饮'
    if any(k in text for k in ['出租', '滴滴', '加油', '地铁', '公交', '停车', '高铁', '火车', '机票', '航空', '高德', '打车']):
        return '交通'
    if any(k in text for k in ['电影', '游戏', 'ktv', '娱乐', '旅游', '酒店']):
        return '娱乐'
    if any(k in text for k in ['医院', '药', '诊所', '医']):
        return '医疗'
    if any(k in text for k in ['房租', '物业', '水费', '电费', '燃气', '宽带']):
        return '住房'
    if any(k in text for k in ['apple', '苹果', 'icloud', '订阅']):
        return '订阅'
    return '其他'


def match_pay_method(pay_method: str, accounts: list[dict], liabilities: list[dict] | None = None) -> dict | None:
    """Match payment method string to an account or liability.

    Returns {'type': 'account', 'id': ...} or {'type': 'liability', 'id': ...} or None.
    """
    if not pay_method:
        return None
    pm = pay_method.replace('（', '(').replace('）', ')')
    # Remove suffixes like "&红包", "&优惠"
    pm = re.sub(r'[&＆].*$', '', pm).strip()

    # Check credit cards in liabilities first
    if liabilities:
        for liab in liabilities:
            if liab.get('type') != 'credit_card':
                continue
            name = liab.get('name', '')
            # Extract bank name from liability name (e.g. "广发银行信用卡" -> "广发")
            bank = re.sub(r'(银行|信用卡|储蓄卡|借记卡)', '', name).strip()
            if bank and bank in pm:
                return {'type': 'liability', 'id': liab['id']}

    # Skip non-account methods
    if any(k in pm for k in ['零钱', '余额宝', '花呗', '退款', '积分', '红包']):
        for acc in accounts:
            if '余额宝' in pm and '余额宝' in acc.get('name', ''):
                return {'type': 'account', 'id': acc['id']}
            if '支付宝' in acc.get('type', '') and ('余额' in pm or '零钱' in pm):
                return {'type': 'account', 'id': acc['id']}
        return None
    # Try to match bank + card type
    for acc in accounts:
        if not acc.get('institution'):
            continue
        inst = acc['institution']
        if inst in pm:
            return {'type': 'account', 'id': acc['id']}
    # Fallback: try matching bank name from pay_method
    bank_match = re.search(r'([一-龥]{2,6}银行)', pm)
    if bank_match:
        bank_name = bank_match.group(1)
        for acc in accounts:
            if acc.get('institution') and bank_name in acc['institution']:
                return {'type': 'account', 'id': acc['id']}
    return None
