import pandas as pd

order_data = {
    'MaDonHang': ['DH001', 'DH002', 'DH003', 'DH004', 'DH005'],
    'TenSanPham': ['Laptop', 'Bàn phím', 'Chuột', 'Màn hình', 'Laptop'],
    'SoLuong': [5, 10, 15, 8, 3],
    'DanhGia': [4.5, 4.0, 5.0, 4.2, 4.8]
}

df_orders = pd.DataFrame(order_data)
print(f"DataFrame ban đầu:\n{df_orders}")

df_orders['DonGia'] = [18000, 500, 350, 4500, 19500]
print(f"DataFrame sau khi thêm đơn giá:\n{df_orders}")

df_orders['ThanhTien'] = df_orders['SoLuong'] * df_orders['DonGia']
df_sorted_orders = df_orders.sort_values(by='ThanhTien', ascending=False)
print(f"DataFrame sau khi sắp xếp theo thành tiền:\n{df_sorted_orders}")
