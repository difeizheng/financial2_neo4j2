"""单元测试 - Excel函数"""
import pytest
from financial_kg.core.formula_functions import *


class TestExcelFunctions:
    """Excel函数测试"""

    # === 数学函数 ===

    def test_sum_numbers(self):
        assert SUM(1, 2, 3) == 6

    def test_sum_with_list(self):
        assert SUM([1, 2, 3]) == 6

    def test_sum_mixed(self):
        assert SUM(1, [2, 3], 4) == 10

    def test_sum_with_none(self):
        assert SUM(1, None, 2) == 3

    def test_average(self):
        assert AVERAGE(1, 2, 3) == 2

    def test_average_with_list(self):
        assert AVERAGE([1, 2, 3, 4]) == 2.5

    def test_max(self):
        assert MAX(1, 5, 3) == 5

    def test_max_with_list(self):
        assert MAX([1, 2, 3]) == 3

    def test_min(self):
        assert MIN(1, 5, 3) == 1

    def test_min_with_list(self):
        assert MIN([1, 2, 3]) == 1

    def test_abs_positive(self):
        assert ABS(5) == 5

    def test_abs_negative(self):
        assert ABS(-5) == 5

    def test_power(self):
        assert POWER(2, 3) == 8

    def test_sqrt(self):
        assert SQRT(9) == 3

    def test_sqrt_negative(self):
        assert SQRT(-1) is None

    def test_int(self):
        assert INT(3.7) == 3

    def test_int_negative(self):
        assert INT(-3.7) == -4

    def test_mod(self):
        assert MOD(10, 3) == 1

    def test_mod_zero(self):
        assert MOD(10, 0) is None

    # === 取整函数 ===

    def test_round(self):
        assert ROUND(1.567, 2) == 1.57

    def test_round_zero_digits(self):
        assert ROUND(1.567, 0) == 2

    def test_roundup(self):
        assert ROUNDUP(1.234, 2) == 1.24

    def test_roundup_negative(self):
        assert ROUNDUP(-1.234, 2) == -1.23

    def test_rounddown(self):
        assert ROUNDDOWN(1.567, 2) == 1.56

    # === 条件函数 ===

    def test_if_true(self):
        assert IF(1, "yes", "no") == "yes"

    def test_if_false(self):
        assert IF(0, "yes", "no") == "no"

    def test_if_with_condition(self):
        assert IF(5 > 3, 100, 0) == 100

    def test_iferror_with_error(self):
        assert IFERROR(None, "error") == "error"

    def test_iferror_with_value(self):
        assert IFERROR(100, "error") == 100

    def test_sumif(self):
        data = [1, 2, 3, 4, 5]
        assert SUMIF(data, ">3") == 9  # 4+5

    def test_countif(self):
        data = [1, 2, 3, 4, 5]
        assert COUNTIF(data, ">3") == 2

    # === 逻辑函数 ===

    def test_and_true(self):
        assert AND(1, 1, 1) == True

    def test_and_false(self):
        assert AND(1, 0, 1) == False

    def test_or_true(self):
        assert OR(0, 1, 0) == True

    def test_or_false(self):
        assert OR(0, 0, 0) == False

    def test_not(self):
        assert NOT(1) == False
        assert NOT(0) == True

    # === 日期函数 ===

    def test_year(self):
        from datetime import date
        assert YEAR(date(2024, 5, 15)) == 2024

    def test_month(self):
        from datetime import date
        assert MONTH(date(2024, 5, 15)) == 5

    def test_day(self):
        from datetime import date
        assert DAY(date(2024, 5, 15)) == 15

    def test_edate(self):
        from datetime import date
        result = EDATE(date(2024, 1, 15), 2)
        assert result.month == 3

    def test_datedif_years(self):
        from datetime import date
        start = date(2020, 1, 1)
        end = date(2024, 1, 1)
        assert DATEDIF(start, end, "Y") == 4

    def test_datedif_months(self):
        from datetime import date
        start = date(2024, 1, 1)
        end = date(2024, 5, 1)
        assert DATEDIF(start, end, "M") == 4

    def test_datedif_days(self):
        from datetime import date
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)
        assert DATEDIF(start, end, "D") == 30

    # === 统计函数 ===

    def test_count(self):
        assert COUNT(1, 2, None, "text") == 2

    def test_counta(self):
        assert COUNTA(1, 2, None, "") == 2

    def test_large(self):
        assert LARGE([1, 5, 3, 2, 4], 2) == 4

    def test_small(self):
        assert SMALL([1, 5, 3, 2, 4], 2) == 2

    # === 财务函数 ===

    def test_pv(self):
        # PV(rate=5%, nper=10, pmt=-100)
        result = PV(0.05, 10, -100)
        assert result > 0  # 现值应该为正

    def test_fv(self):
        # FV(rate=5%, nper=10, pmt=-100)
        result = FV(0.05, 10, -100)
        assert result > 0  # 终值应该为正

    def test_sln(self):
        # 直线折旧
        assert SLN(10000, 1000, 10) == 900

    # === 查找函数 ===

    def test_index(self):
        data = [[1, 2, 3], [4, 5, 6]]
        assert INDEX(data, 2, 3) == 6

    def test_index_one_dim(self):
        data = [1, 2, 3, 4, 5]
        assert INDEX(data, 3) == 3

    def test_match_exact(self):
        data = [1, 2, 3, 4, 5]
        assert MATCH(3, data, 0) == 3

    def test_vlookup_exact(self):
        data = [["A", 100], ["B", 200], ["C", 300]]
        assert VLOOKUP("B", data, 2, False) == 200

    # === 文本函数 ===

    def test_len(self):
        assert LEN("Hello") == 5

    def test_left(self):
        assert LEFT("Hello", 2) == "He"

    def test_right(self):
        assert RIGHT("Hello", 2) == "lo"

    def test_mid(self):
        assert MID("Hello", 2, 3) == "ell"

    def test_concatenate(self):
        assert CONCATENATE("A", "B", "C") == "ABC"

    def test_trim(self):
        assert TRIM("  Hello  ") == "Hello"

    def test_value(self):
        assert VALUE("123") == 123

    def test_value_percentage(self):
        assert VALUE("50%") == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])