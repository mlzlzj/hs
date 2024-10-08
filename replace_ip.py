import itertools
import requests
import threading
import os
import time

# 根据给定的IP地址，端口和扫描类型生成所有可能的IP地址
def generate_ip_combinations(base_ip, scan_type='1'):
    parts = base_ip.split('.')
    A, B, C, D = parts[0], parts[1], parts[2], parts[3]

    if scan_type == '1':  # 扫描D段
        C_range = [C]
        D_range = range(0, 256)
    elif scan_type == '2':  # 扫描C段和D段
        C_range = range(0, 256)
        D_range = range(0, 256)

    all_ips = []
    for C, D in itertools.product(C_range, D_range):
        all_ips.append(f"{A}.{B}.{C}.{D}")

    return all_ips


# 检查链接是否有效（HTTP状态码200），并将结果写入集合。
def check_link(link, result_set, response_times, progress_lock, progress_counter, total_count):
    try:
        start_time = time.time()  # 记录请求发送前的当前时间
        response = requests.get(link, timeout=5)
        end_time = time.time()  # 记录请求完成后的当前时间

        response_time_ms = (end_time - start_time) * 1000  # 计算响应时间，单位为毫秒

        with progress_lock:
            progress_counter[0] += 1
            progress = (progress_counter[0] / total_count) * 100
            if "EXTM3U" in response.text:
                result_set.add(link)
                ip_with_port = link.split('/')[2].split(':')[0] + ":" + link.split('/')[2].split(':')[1]
                response_times[ip_with_port] = response_time_ms  # 存储响应时间
                print(f"[{progress_counter[0]}/{total_count} - {progress:.2f}%] 成功: {link} [响应时间: {response_time_ms:.2f} ms]")
            else:
                print(f"[{progress_counter[0]}/{total_count} - {progress:.2f}%] 失败: {link} [响应时间: {response_time_ms:.2f} ms]")
    except Exception as e:
        with progress_lock:
            progress_counter[0] += 1
            progress = (progress_counter[0] / total_count) * 100
            print(f"[{progress_counter[0]}/{total_count} - {progress:.2f}%] 失败: {link} [错误: {str(e)}]")


# 将结果写入以地区名称_iptv.txt为文件名的文件中
def write_results(result_set, port, muban, region, output_folder):
    file_path = os.path.join(output_folder, f"{region}_iptv.txt")

    with open(file_path, "w", encoding="utf-8") as file:
        # 写入标题
        file.write(f"{region}频道,#genre#\n")
        # 写入所有的频道列表
        for valid_link in result_set:
            ip = valid_link.split('/')[2].split(':')[0]
            result_content = muban.replace("ip", f"{ip}:{port}")
            file.write(f"{result_content}\n")


def read_config(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        configs = [line.strip().split(',') for line in f]
    return configs


def merge_files(output_folder, zdy_file_path):
    # 获取所有_iptv.txt文件的路径
    iptv_files = [f for f in os.listdir(output_folder) if f.endswith('_iptv.txt')]

    # 合并所有_iptv.txt文件的内容
    merged_content = ""
    for iptv_file in iptv_files:
        file_path = os.path.join(output_folder, iptv_file)
        with open(file_path, "r", encoding="utf-8") as file:
            merged_content += file.read() + "\n"

    # 检查zdy.txt文件是否存在
    if os.path.exists(zdy_file_path):
        # 读取zdy.txt文件的内容
        with open(zdy_file_path, "r", encoding="utf-8") as zdy_file:
            zdy_content = zdy_file.read()
        # 合并zdy.txt和_iptv.txt文件的内容
        final_content = merged_content + "\n" + zdy_content
    else:
        final_content = merged_content

    # 将合并后的内容写入iptv_list.txt文件
    iptv_list_file_path = "iptv_list.txt"
    with open(iptv_list_file_path, "w", encoding="utf-8") as iptv_list_file:
        iptv_list_file.write(final_content)

    print(f"\n所有地区频道列表文件合并完成，文件保存为：{iptv_list_file_path}")


def main():
    # 获取地区模板文件夹下的所有模板文件
    template_directory = "地区模板"
    template_files = [f for f in os.listdir(template_directory) if f.endswith('.txt')]
    # 提取模板名称
    template_names = [os.path.splitext(file)[0] for file in template_files]

    # 打印显示所有地区模板文件夹下的所有模板名称
    print(f"......开始扫描 {' '.join(template_names)} 地区的频道列表......")

    # 从config.txt读取配置信息
    config_path = 'config.txt'
    try:
        configs = read_config(config_path)
    except ValueError:
        print(f"配置文件 {config_path} 格式错误。")
        return

    # 检查并创建“地区频道”文件夹
    output_folder = "地区频道"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 在主函数中添加存储响应时间的字典
    all_valid_ips = {}  # 用于存储所有地区的有效IP地址
    all_response_times = {}  # 用于存储所有地区的有效IP的响应时间

    for config in configs:
        try:
            region, scan_link, ip, port, scan_type = config
        except ValueError:
            print(f"配置文件 {config_path} 中格式错误。")
            continue

        # 读取对应地区.txt文件内容
        try:
            with open(f"地区模板/{region}.txt", "r", encoding="utf-8") as file:
                muban = file.read()
        except FileNotFoundError:
            print(f"文件 地区模板/{region}.txt 未找到。")
            continue

        # 生成所选范围的IP组合
        all_ips = generate_ip_combinations(ip, scan_type)

        # 检查链接的完整URL
        links = [scan_link.replace("{ip}", ip).replace("{port}", port) for ip in all_ips]

        result_set = set()  # 使用集合存储有效链接
        response_times = {}  # 用于存储每个有效IP的响应时间
        progress_counter = [0]  # 共享的进度计数器
        progress_lock = threading.Lock()  # 锁用于同步访问计数器
        total_count = len(links)  # 总链接数

        # 多线程检查链接
        threads = []
        for link in links:
            thread = threading.Thread(target=check_link,
                                      args=(
                                      link, result_set, response_times, progress_lock, progress_counter, total_count))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # 确保所有线程完成后最终写入结果
        write_results(result_set, port, muban, region, output_folder)

        # 提示扫描结束
        print(f"{region}找到的有效链接总数: {len(result_set)}")
        print(f"{region}扫描完成,文件保存为：{region}_iptv.txt\n")

        # 收集每个地区的所有有效IP地址及其响应时间
        for valid_link in result_set:
            ip_with_port = valid_link.split('/')[2].split(':')[0] + ":" + port
            all_valid_ips.setdefault(region, []).append(ip_with_port)
            # 将响应时间也添加到对应地区的列表中
            if ip_with_port in response_times:
                all_response_times.setdefault(region, []).append(response_times[ip_with_port])

        # 集中打印出所有地区的所有有效IP地址及其响应时间
    for region, ips in all_valid_ips.items():
        print(f"\n本次扫描找到{region}有效ip：")
        for ip, response_time in zip(ips, all_response_times.get(region, [])):
            print(f"{ip}   响应时间: {response_time:.2f} ms")

    # 合并文件
    output_folder = "地区频道"
    zdy_file_path = "zdy.txt"
    merge_files(output_folder, zdy_file_path)


if __name__ == "__main__":
    main()
