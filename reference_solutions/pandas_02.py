import pandas as pd

employee_data = {
    'Ten': ['Anh', 'Bình', 'Hương', 'Khang', 'Lan', 'Minh'],
    'PhongBan': ['Nhân sự', 'Kinh doanh', 'Marketing', 'Kinh doanh', 'Marketing', 'Nhân sự'],
    'NamKinhNghiem': [3, 5, 2, 5, 4, 3],
    'LuongThang': [15, 22, 18, 24, 20, 16]
}

df_employees = pd.DataFrame(employee_data)
print(f"DataFrame dữ liệu nhân sự:\n{df_employees}")

so_nv_kinh_nghiem = df_employees[df_employees['NamKinhNghiem'] > 3].shape[0]
print(f"Số nhân viên có hơn 3 năm kinh nghiệm: {so_nv_kinh_nghiem}")

so_nv_luong_cao = df_employees[
    (df_employees['PhongBan'] == 'Kinh doanh') &
    (df_employees['LuongThang'] * 12 > 250)
].shape[0]
print(f"Số nhân viên phòng Kinh doanh có lương năm > 250 triệu: {so_nv_luong_cao}")
