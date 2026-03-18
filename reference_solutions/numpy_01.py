import numpy as np

gia_ban = np.array([250, 400, 320, 150, 500])
chi_phi = np.array([180, 290, 250, 90, 370])
so_luong_ban = np.array([120, 85, 150, 210, 70])

tong_doanh_thu = gia_ban * so_luong_ban
print(f"Tổng doanh thu cho từng sản phẩm là: {tong_doanh_thu}")

tong_loi_nhuan = np.sum((gia_ban - chi_phi) * so_luong_ban)
print(f"Tổng lợi nhuận của công ty là: {tong_loi_nhuan*1000:,.0f} VND")

loi_nhuan_moi_sp = (gia_ban - chi_phi) * so_luong_ban
so_san_pham = np.sum(loi_nhuan_moi_sp >= 10000)
print(f"Số lượng sản phẩm có lợi nhuận lớn hơn hoặc bằng 10 triệu VNĐ là: {so_san_pham}")
