# Case 9: Logic Error - Mutable default argument in function
def record_student_grade(grade, grade_list=[]):
    # Bug: mutable default list persists state between invocations
    grade_list.append(grade)
    return grade_list

first_student = record_student_grade(90)
second_student = record_student_grade(85)
print("Second Student Grades:", second_student)
