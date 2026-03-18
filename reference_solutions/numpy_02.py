import numpy as np

sales_matrix = np.array([
    [302, 635, 470, 306],
    [271, 220, 321, 666],
    [414, 530, 658, 287],
    [572, 299, 330, 508]
])

trung_binh_khu_vuc = np.mean(sales_matrix, axis=1)
print(f"Doanh số trung bình mỗi khu vực: {trung_binh_khu_vuc}")

tong_doanh_so_quy = np.sum(sales_matrix, axis=0)
print(f"Tổng doanh số theo từng quý: {tong_doanh_so_quy}")

quy_vuot_troi = sales_matrix[sales_matrix > 650]
print(f"Các kết quả doanh số vượt mục tiêu 650: {quy_vuot_troi}")

tang_truong_Q1_Q4 = ((sales_matrix[:, 3] - sales_matrix[:, 0]) / sales_matrix[:, 0]) * 100
print(f"Tăng trưởng doanh số từ Q1 đến Q4 của mỗi khu vực (%): {np.round(tang_truong_Q1_Q4, 2)}")
