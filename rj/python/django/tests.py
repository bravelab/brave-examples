import pytest

from datetime import date

from django.core.management import call_command
from django.core.exceptions import ValidationError

from cdo.edu.management.models import (Student, StudentState)
from cdo.edu.division.models import Division

@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command('loaddata', 'cdo/edu/unit/fixtures/test_unit.json')
        call_command('loaddata', 'cdo/edu/management/fixtures/test_management.json')

@pytest.mark.django_db
@pytest.mark.parametrize("date_check,expected_count", [
    (date(2015, 8, 1), 0),
    (date(2015, 9, 1), 1),
    (date(2015, 10, 1), 0),
    (date(2015, 11, 1), 0),
])

def test_division_count(date_check, expected_count):
    division = Division.objects.first()
    start_date, end_date = date(2015, 9, 1), date(2015, 10, 1)
    student = Student.objects.first()
    StudentState(division=division, parent=student, start_date=start_date, end_date=end_date).save()
    assert division.get_count(date_check) == expected_count

@pytest.mark.django_db
@pytest.mark.parametrize("start_date,end_date", [
    (date(2015, 9, 1), date(2019, 9, 1)),
    (date(2015, 9, 1), date(2016, 9, 2)),
    (date(2015, 9, 1), None),
    (date(2015, 9, 2), None),
    (date(2012, 9, 1), date(2020, 9, 1)),  # student stay dates
    pytest.param(date(2012, 8, 1), date(2020, 10, 1), marks=pytest.mark.xfail(raises=ValidationError)),
    pytest.param(date(2015, 9, 1), date(2015, 9, 1), marks=pytest.mark.xfail(raises=ValidationError)),
    pytest.param(date(2015, 9, 2), date(2015, 10, 1), marks=pytest.mark.xfail(raises=ValidationError)),
    pytest.param(date(2015, 9, 1), date(2010, 9, 1), marks=pytest.mark.xfail(raises=ValidationError)),
])

def test_student_state(start_date, end_date):
    student = Student.objects.first()
    division = Division.objects.filter(category=None).first()
    student_state = StudentState(start_date=start_date, end_date=end_date, parent=student, division=division)
    student_state.full_clean()
