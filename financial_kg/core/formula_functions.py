"""Excel函数实现 - 核心函数集"""
import math
from typing import Any, List, Union, Optional
from datetime import datetime, date, timedelta
import numpy as np


Number = Union[int, float]


def SUM(*args) -> Number:
    """求和 - 支持数字和范围"""
    total = 0
    for arg in args:
        if isinstance(arg, (list, tuple)):
            for item in arg:
                if isinstance(item, (int, float)) and item is not None:
                    total += item
        elif isinstance(arg, (int, float)) and arg is not None:
            total += arg
    return total


def IF(condition: Any, true_value: Any, false_value: Any = None) -> Any:
    """条件判断"""
    # Excel中非零和非空为TRUE
    if _is_true(condition):
        return true_value
    return false_value


def _is_true(value: Any) -> bool:
    """判断值是否为真（Excel逻辑）"""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.upper() == "TRUE" or len(value) > 0
    return True


def ROUND(number: Number, digits: int = 0) -> Number:
    """四舍五入"""
    if number is None:
        return None
    return round(number, digits)


def ROUNDUP(number: Number, digits: int = 0) -> Number:
    """向上取整"""
    if number is None:
        return None
    if digits == 0:
        return math.ceil(number)
    multiplier = 10 ** digits
    return math.ceil(number * multiplier) / multiplier


def ROUNDDOWN(number: Number, digits: int = 0) -> Number:
    """向下取整"""
    if number is None:
        return None
    if digits == 0:
        return math.floor(number)
    multiplier = 10 ** digits
    return math.floor(number * multiplier) / multiplier


def MAX(*args) -> Number:
    """最大值"""
    values = _flatten_numbers(args)
    if not values:
        return 0
    return max(values)


def MIN(*args) -> Number:
    """最小值"""
    values = _flatten_numbers(args)
    if not values:
        return 0
    return min(values)


def ABS(number: Number) -> Number:
    """绝对值"""
    if number is None:
        return None
    return abs(number)


def SUMIF(range_data: List, criteria: Any, sum_range: List = None) -> Number:
    """条件求和"""
    if sum_range is None:
        sum_range = range_data

    total = 0
    for i, val in enumerate(range_data):
        if _matches_criteria(val, criteria):
            if i < len(sum_range) and isinstance(sum_range[i], (int, float)):
                total += sum_range[i]
    return total


def COUNTIF(range_data: List, criteria: Any) -> int:
    """条件计数"""
    count = 0
    for val in range_data:
        if _matches_criteria(val, criteria):
            count += 1
    return count


def _matches_criteria(value: Any, criteria: Any) -> bool:
    """判断值是否满足条件"""
    if criteria is None:
        return value is None

    # 字符串条件
    if isinstance(criteria, str):
        # 比较操作符
        if criteria.startswith(">="):
            return isinstance(value, (int, float)) and value >= float(criteria[2:])
        if criteria.startswith("<="):
            return isinstance(value, (int, float)) and value <= float(criteria[2:])
        if criteria.startswith(">"):
            return isinstance(value, (int, float)) and value > float(criteria[1:])
        if criteria.startswith("<"):
            return isinstance(value, (int, float)) and value < float(criteria[1:])
        if criteria.startswith("="):
            return str(value) == criteria[1:]

    # 直接比较
    return value == criteria


def DATEDIF(start_date: Any, end_date: Any, unit: str) -> Number:
    """日期差 - Excel中常用计算年份/月份差"""
    # 解析日期
    start = _parse_date(start_date)
    end = _parse_date(end_date)

    if start is None or end is None:
        return None

    unit = unit.upper()

    if unit == "Y":
        # 年份差
        years = end.year - start.year
        if (end.month, end.day) < (start.month, start.day):
            years -= 1
        return years
    elif unit == "M":
        # 月份差
        months = (end.year - start.year) * 12 + end.month - start.month
        if end.day < start.day:
            months -= 1
        return months
    elif unit == "D":
        # 天数差
        return (end - start).days
    elif unit == "YM":
        # 忽略年的月份差
        months = end.month - start.month
        if end.day < start.day:
            months -= 1
        return months
    elif unit == "YD":
        # 忽略年的天数差
        # 简化实现
        return (end - start).days % 365
    elif unit == "MD":
        # 忽略年月的天数差
        return end.day - start.day

    return None


def _parse_date(value: Any) -> date:
    """解析日期值"""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        # 尝试常见格式
        for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y"]:
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    if isinstance(value, (int, float)):
        # Excel日期序列号（从1900-01-01起）
        # 注意：Excel有1900年bug，需调整
        return date(1900, 1, 1) + timedelta(days=int(value) - 2)
    return None


def AND(*args) -> bool:
    """逻辑与"""
    for arg in args:
        if isinstance(arg, (list, tuple)):
            for item in arg:
                if not _is_true(item):
                    return False
        elif not _is_true(arg):
            return False
    return True


def OR(*args) -> bool:
    """逻辑或"""
    for arg in args:
        if isinstance(arg, (list, tuple)):
            for item in arg:
                if _is_true(item):
                    return True
        elif _is_true(arg):
            return True
    return False


def NOT(value: Any) -> bool:
    """逻辑非"""
    return not _is_true(value)


def _flatten_numbers(args) -> List[Number]:
    """展平参数中的数字"""
    result = []
    for arg in args:
        if isinstance(arg, (list, tuple)):
            for item in arg:
                if isinstance(item, (int, float)) and item is not None:
                    result.append(item)
        elif isinstance(arg, (int, float)) and arg is not None:
            result.append(arg)
    return result


# === 日期函数 ===

def YEAR(date_value: Any) -> Optional[int]:
    """提取年份"""
    d = _parse_date(date_value)
    if d is None:
        return None
    return d.year


def MONTH(date_value: Any) -> Optional[int]:
    """提取月份"""
    d = _parse_date(date_value)
    if d is None:
        return None
    return d.month


def DAY(date_value: Any) -> Optional[int]:
    """提取日"""
    d = _parse_date(date_value)
    if d is None:
        return None
    return d.day


def EDATE(start_date: Any, months: Number) -> Optional[date]:
    """日期偏移 - 返回偏移后的日期"""
    d = _parse_date(start_date)
    if d is None or months is None:
        return None

    # 计算新日期
    new_year = d.year + int((d.month + months - 1) // 12)
    new_month = int((d.month + months - 1) % 12) + 1

    # 处理日期溢出
    try:
        return date(new_year, new_month, d.day)
    except ValueError:
        # 日期溢出（如1月31日+1月），返回月末
        import calendar
        last_day = calendar.monthrange(new_year, new_month)[1]
        return date(new_year, new_month, last_day)


def DATE(year: int, month: int, day: int) -> date:
    """构造日期"""
    try:
        return date(year, month, day)
    except ValueError:
        return None


def TODAY() -> date:
    """返回当前日期"""
    return date.today()


# === 统计函数 ===

def AVERAGE(*args) -> Number:
    """平均值"""
    values = _flatten_numbers(args)
    if not values:
        return 0
    return sum(values) / len(values)


def COUNT(*args) -> int:
    """计数 - 统计数值个数"""
    count = 0
    for arg in args:
        if isinstance(arg, (list, tuple)):
            for item in arg:
                if isinstance(item, (int, float)) and item is not None:
                    count += 1
        elif isinstance(arg, (int, float)) and arg is not None:
            count += 1
    return count


def COUNTA(*args) -> int:
    """计数 - 统计非空值个数"""
    count = 0
    for arg in args:
        if isinstance(arg, (list, tuple)):
            for item in arg:
                if item is not None and item != "":
                    count += 1
        elif arg is not None and arg != "":
            count += 1
    return count


def LARGE(range_data: List, k: int) -> Number:
    """第k大值"""
    values = _flatten_numbers([range_data])
    if not values or k <= 0 or k > len(values):
        return None
    values.sort(reverse=True)
    return values[k - 1]


def SMALL(range_data: List, k: int) -> Number:
    """第k小值"""
    values = _flatten_numbers([range_data])
    if not values or k <= 0 or k > len(values):
        return None
    values.sort()
    return values[k - 1]


# === 数学函数 ===

def POWER(number: Number, power: Number) -> Number:
    """幂运算"""
    if number is None or power is None:
        return None
    return number ** power


def SQRT(number: Number) -> Number:
    """平方根"""
    if number is None:
        return None
    if number < 0:
        return None  # Excel返回#NUM!错误
    return math.sqrt(number)


def INT(number: Number) -> int:
    """向下取整"""
    if number is None:
        return None
    return int(math.floor(number))


def MOD(number: Number, divisor: Number) -> Number:
    """取模"""
    if number is None or divisor is None or divisor == 0:
        return None
    return number - divisor * INT(number / divisor)


def LN(number: Number) -> Number:
    """自然对数"""
    if number is None or number <= 0:
        return None
    return math.log(number)


def LOG(number: Number, base: Number = 10) -> Number:
    """对数"""
    if number is None or number <= 0 or base is None or base <= 0:
        return None
    return math.log(number, base)


def EXP(number: Number) -> Number:
    """e的幂"""
    if number is None:
        return None
    return math.exp(number)


def SIGN(number: Number) -> int:
    """符号"""
    if number is None:
        return None
    if number > 0:
        return 1
    elif number < 0:
        return -1
    return 0


# === 财务函数 ===

def IRR(values: List, guess: Number = 0.1) -> Number:
    """内部收益率"""
    if not values or len(values) < 2:
        return None

    try:
        # 使用numpy的IRR计算
        return np.irr(values) * 100  # 转换为百分比
    except (ValueError, RuntimeError):
        return None


def NPV(rate: Number, *values) -> Number:
    """净现值"""
    if rate is None:
        return None

    result = 0
    for i, val in enumerate(values):
        if isinstance(val, (list, tuple)):
            for j, v in enumerate(val):
                if isinstance(v, (int, float)) and v is not None:
                    result += v / ((1 + rate) ** (i + j + 1))
        elif isinstance(val, (int, float)) and val is not None:
            result += val / ((1 + rate) ** (i + 1))
    return result


def PV(rate: Number, nper: Number, pmt: Number, fv: Number = 0, type: int = 0) -> Number:
    """现值"""
    if rate is None or nper is None or pmt is None:
        return None

    if rate == 0:
        return -pmt * nper - fv

    factor = (1 + rate) ** nper
    pv = -(pmt * (1 + rate * type) * (factor - 1) / rate + fv) / factor
    return pv


def FV(rate: Number, nper: Number, pmt: Number, pv: Number = 0, type: int = 0) -> Number:
    """终值"""
    if rate is None or nper is None or pmt is None:
        return None

    if rate == 0:
        return -pv - pmt * nper

    factor = (1 + rate) ** nper
    fv = -pv * factor - pmt * (1 + rate * type) * (factor - 1) / rate
    return fv


def PMT(rate: Number, nper: Number, pv: Number, fv: Number = 0, type: int = 0) -> Number:
    """分期付款"""
    if rate is None or nper is None or pv is None:
        return None

    if rate == 0:
        return -(pv + fv) / nper

    factor = (1 + rate) ** nper
    pmt = -(pv * factor + fv) * rate / ((1 + rate * type) * (factor - 1))
    return pmt


def SLN(cost: Number, salvage: Number, life: Number) -> Number:
    """直线折旧"""
    if cost is None or salvage is None or life is None or life == 0:
        return None
    return (cost - salvage) / life


def SYD(cost: Number, salvage: Number, life: Number, period: Number) -> Number:
    """年数总和折旧"""
    if any(x is None for x in [cost, salvage, life, period]) or life == 0:
        return None
    return (cost - salvage) * (life - period + 1) * 2 / (life * (life + 1))


# === 错误处理 ===

def IFERROR(value: Any, value_if_error: Any) -> Any:
    """错误处理"""
    if value is None:
        return value_if_error

    # 检查是否是错误类型
    error_types = [None, "#N/A", "#VALUE!", "#REF!", "#DIV/0!", "#NUM!", "#NAME?", "#NULL!"]
    if value in error_types or isinstance(value, str) and value.startswith("#"):
        return value_if_error

    return value


def IFNA(value: Any, value_if_na: Any) -> Any:
    """处理#N/A错误"""
    if value is None or value == "#N/A":
        return value_if_na
    return value


# === 查找函数 ===

def INDEX(array: List, row_num: int, col_num: int = 1) -> Any:
    """索引查找"""
    if not array or row_num is None:
        return None

    # 处理二维数组
    if isinstance(array[0], (list, tuple)):
        if row_num <= 0 or row_num > len(array):
            return None
        row = array[row_num - 1]
        if col_num <= 0 or col_num > len(row):
            return None
        return row[col_num - 1]
    else:
        # 一维数组
        if row_num <= 0 or row_num > len(array):
            return None
        return array[row_num - 1]


def MATCH(lookup_value: Any, lookup_array: List, match_type: int = 1) -> int:
    """匹配查找"""
    if lookup_value is None or not lookup_array:
        return None

    if match_type == 0:
        # 精确匹配
        for i, val in enumerate(lookup_array):
            if val == lookup_value:
                return i + 1
        return None

    elif match_type == 1:
        # 小于或等于的最大值（数组需升序）
        result = None
        for i, val in enumerate(lookup_array):
            if isinstance(val, (int, float)) and isinstance(lookup_value, (int, float)):
                if val <= lookup_value:
                    result = i + 1
                else:
                    break
        return result

    elif match_type == -1:
        # 大于或等于的最小值（数组需降序）
        result = None
        for i, val in enumerate(lookup_array):
            if isinstance(val, (int, float)) and isinstance(lookup_value, (int, float)):
                if val >= lookup_value:
                    result = i + 1
                else:
                    break
        return result

    return None


def VLOOKUP(lookup_value: Any, table_array: List, col_index_num: int, range_lookup: bool = True) -> Any:
    """垂直查找"""
    if lookup_value is None or not table_array or col_index_num is None:
        return None

    if col_index_num <= 0:
        return None

    # 在第一列查找
    for i, row in enumerate(table_array):
        if isinstance(row, (list, tuple)) and len(row) > 0:
            first_col = row[0]

            if range_lookup:
                # 近似匹配（第一列需升序）
                if isinstance(first_col, (int, float)) and isinstance(lookup_value, (int, float)):
                    if first_col <= lookup_value:
                        if col_index_num <= len(row):
                            return row[col_index_num - 1]
                    else:
                        break
            else:
                # 精确匹配
                if first_col == lookup_value:
                    if col_index_num <= len(row):
                        return row[col_index_num - 1]
                    return None

    return None


def HLOOKUP(lookup_value: Any, table_array: List, row_index_num: int, range_lookup: bool = True) -> Any:
    """水平查找"""
    if lookup_value is None or not table_array or row_index_num is None:
        return None

    if row_index_num <= 0 or row_index_num > len(table_array):
        return None

    # 在第一行查找
    first_row = table_array[0]
    if not isinstance(first_row, (list, tuple)):
        return None

    for j, val in enumerate(first_row):
        if range_lookup:
            if isinstance(val, (int, float)) and isinstance(lookup_value, (int, float)):
                if val <= lookup_value:
                    if j < len(table_array[row_index_num - 1]):
                        return table_array[row_index_num - 1][j]
                else:
                    break
        else:
            if val == lookup_value:
                if j < len(table_array[row_index_num - 1]):
                    return table_array[row_index_num - 1][j]

    return None


# === 文本函数 ===

def LEN(text: str) -> int:
    """字符串长度"""
    if text is None:
        return 0
    return len(str(text))


def LEFT(text: str, num_chars: int = 1) -> str:
    """左侧截取"""
    if text is None:
        return ""
    return str(text)[:num_chars]


def RIGHT(text: str, num_chars: int = 1) -> str:
    """右侧截取"""
    if text is None:
        return ""
    text = str(text)
    if num_chars >= len(text):
        return text
    return text[-num_chars:]


def MID(text: str, start_num: int, num_chars: int) -> str:
    """中间截取"""
    if text is None or start_num is None or num_chars is None:
        return ""
    text = str(text)
    if start_num <= 0:
        return ""
    return text[start_num - 1:start_num - 1 + num_chars]


def CONCATENATE(*args) -> str:
    """字符串连接"""
    result = ""
    for arg in args:
        if arg is not None:
            result += str(arg)
    return result


def TRIM(text: str) -> str:
    """去除空格"""
    if text is None:
        return ""
    return str(text).strip()


def VALUE(text: str) -> Number:
    """文本转数值"""
    if text is None:
        return None
    try:
        text = str(text).strip()
        if text.endswith("%"):
            return float(text[:-1]) / 100
        return float(text)
    except ValueError:
        return None


def TEXT(value: Any, format_text: str) -> str:
    """数值转文本（简化实现）"""
    if value is None:
        return ""

    if isinstance(value, (int, float)):
        # 简化格式处理
        if format_text and format_text.startswith("0"):
            # 数字格式
            return str(value)
        elif "%" in format_text:
            return f"{value * 100}%"

    return str(value)


# === 信息函数 ===

def ISBLANK(value: Any) -> bool:
    """判断单元格是否为空"""
    if value is None:
        return True
    if isinstance(value, str) and value == "":
        return True
    return False


def ISNUMBER(value: Any) -> bool:
    """判断是否为数值"""
    if value is None:
        return False
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def ISTEXT(value: Any) -> bool:
    """判断是否为文本"""
    if value is None:
        return False
    return isinstance(value, str)


def ISERROR(value: Any) -> bool:
    """判断是否为错误值"""
    if value is None:
        return False
    error_types = ["#N/A", "#VALUE!", "#REF!", "#DIV/0!", "#NUM!", "#NAME?", "#NULL!"]
    if isinstance(value, str) and value in error_types:
        return True
    return False


# === 扩展财务函数 ===

def XIRR(values: List, dates: List, guess: Number = 0.1) -> Number:
    """
    计算不规则时间间隔现金流的内部收益率

    参数:
        values: 现金流数组（必须包含至少一个正数和一个负数）
        dates: 对应日期数组（Excel日期序列号或日期对象）
        guess: 初始猜测值（默认0.1）

    返回:
        年化内部收益率
    """
    if not values or not dates or len(values) != len(dates):
        return None
    if len(values) < 2:
        return None

    # 展平数组
    flat_values = []
    flat_dates = []
    for i, v in enumerate(values):
        if isinstance(v, (list, tuple)):
            for j, vv in enumerate(v):
                if vv is not None and isinstance(vv, (int, float)):
                    flat_values.append(vv)
                    d = dates[i]
                    if isinstance(d, (list, tuple)):
                        flat_dates.append(d[j] if j < len(d) else d[-1])
                    else:
                        flat_dates.append(d)
        elif v is not None and isinstance(v, (int, float)):
            flat_values.append(v)
            d = dates[i]
            if isinstance(d, (list, tuple)):
                flat_dates.append(d[0])
            else:
                flat_dates.append(d)

    if len(flat_values) < 2:
        return None

    # 检查是否包含正数和负数
    has_positive = any(v > 0 for v in flat_values)
    has_negative = any(v < 0 for v in flat_values)
    if not (has_positive and has_negative):
        return None

    # 转换日期为天数（从第一个日期开始）
    start_date = flat_dates[0]
    try:
        if isinstance(start_date, (int, float)):
            # Excel日期序列号
            start_days = start_date
        elif isinstance(start_date, date):
            # Python日期对象，转换为Excel序列号
            EXCEL_DATE_BASE = date(1899, 12, 30)
            start_days = (start_date - EXCEL_DATE_BASE).days
        else:
            return None

        day_offsets = []
        for d in flat_dates:
            if isinstance(d, (int, float)):
                day_offsets.append(d - start_days)
            elif isinstance(d, date):
                EXCEL_DATE_BASE = date(1899, 12, 30)
                days = (d - EXCEL_DATE_BASE).days
                day_offsets.append(days - start_days)
            else:
                return None
    except Exception:
        return None

    # Newton-Raphson迭代求解XIRR
    # NPV(rate) = sum(values[i] / (1+rate)^(days[i]/365)) = 0
    rate = guess
    max_iterations = 100
    tolerance = 1e-6

    for _ in range(max_iterations):
        npv = 0
        d_npv = 0  # NPV对rate的导数

        for i, v in enumerate(flat_values):
            years = day_offsets[i] / 365.0
            if years < 0:
                years = 0

            factor = (1 + rate) ** years
            npv += v / factor

            # 导数：d/d(rate) [v / (1+rate)^years] = -v * years / (1+rate)^(years+1)
            if factor > 0:
                d_npv -= v * years / (factor * (1 + rate))

        if abs(npv) < tolerance:
            return rate * 100  # 返回百分比形式

        if d_npv == 0:
            break

        # Newton法更新
        new_rate = rate - npv / d_npv

        # 边界检查
        if new_rate < -0.99:
            new_rate = -0.5
        elif new_rate > 10:
            new_rate = 5

        if abs(new_rate - rate) < tolerance:
            return rate * 100

        rate = new_rate

    return None  # 未收敛


# === 函数注册表 ===
EXCEL_FUNCTIONS = {
    # 数学统计
    "SUM": SUM,
    "AVERAGE": AVERAGE,
    "COUNT": COUNT,
    "COUNTA": COUNTA,
    "MAX": MAX,
    "MIN": MIN,
    "LARGE": LARGE,
    "SMALL": SMALL,

    # 条件函数
    "IF": IF,
    "IFERROR": IFERROR,
    "IFNA": IFNA,
    "SUMIF": SUMIF,
    "COUNTIF": COUNTIF,

    # 取整
    "ROUND": ROUND,
    "ROUNDUP": ROUNDUP,
    "ROUNDDOWN": ROUNDDOWN,
    "INT": INT,
    "ABS": ABS,
    "MOD": MOD,

    # 数学
    "POWER": POWER,
    "SQRT": SQRT,
    "LN": LN,
    "LOG": LOG,
    "EXP": EXP,
    "SIGN": SIGN,

    # 逻辑
    "AND": AND,
    "OR": OR,
    "NOT": NOT,

    # 日期
    "DATEDIF": DATEDIF,
    "YEAR": YEAR,
    "MONTH": MONTH,
    "DAY": DAY,
    "EDATE": EDATE,
    "DATE": DATE,
    "TODAY": TODAY,

    # 财务
    "IRR": IRR,
    "NPV": NPV,
    "PV": PV,
    "FV": FV,
    "PMT": PMT,
    "SLN": SLN,
    "SYD": SYD,
    "XIRR": XIRR,

    # 查找
    "INDEX": INDEX,
    "MATCH": MATCH,
    "VLOOKUP": VLOOKUP,
    "HLOOKUP": HLOOKUP,

    # 文本
    "LEN": LEN,
    "LEFT": LEFT,
    "RIGHT": RIGHT,
    "MID": MID,
    "CONCATENATE": CONCATENATE,
    "TRIM": TRIM,
    "VALUE": VALUE,
    "TEXT": TEXT,

    # 信息
    "ISBLANK": ISBLANK,
    "ISNUMBER": ISNUMBER,
    "ISTEXT": ISTEXT,
    "ISERROR": ISERROR,
}