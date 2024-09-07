import itertools
import requests
import threading
import os


def generate_ip_combinations(base_ip, scan_type='1'):
    parts = base_ip.split('.')
    A, B, C, D = parts[0], parts[1], parts[2], parts[3]

    if scan_type == '1':  # 扫D段
        C_range = [C]
        D_range = range(0, 256)
    elif scan_type == '2':  # C段D段都扫
        C_range = range(0, 256)
        D_range = range(0, 256)

    all_ips = []
    for C, D in itertools.product(C_range, D_range):
        all_ips.append(f"{A}.{B}.{C}.{D}")

    return all_ips


def check_link(link, result_set, progress_lock, progress_counter, total_count):
    try:
        response = requests.get(link, timeout=5)
        with progress_lock:
            progress_counter[0] += 1
            progress = (progress_counter[0] / total_count) * 100
            if response.status_code == 200:
                result_set.add(link)
                print(f"[{progress_counter[0]}/{total_count} - {progress:.2f}%] 成功: {link}")
            else:
                print(f"[{progress_counter[0]}/{total_count} - {progress:.2f}%] 失败: {link}")
    except Exception:
        with progress_lock:
            progress_counter[0] += 1
            progress = (progress_counter[0] / total_count) * 100
            print(f"[{progress_counter[0]}/{total_count} - {progress:.2f}%] 失败: {link}")


def write_results(result_set, port, template_file_name):
    with open(template_file_name, "r", encoding="utf-8") as template_file:
        template_content = template_file.read()

    # 提取地区名称，去掉路径
    area_name = template_file_name.split('/')[-1].split('.')[0]

    output_file_name = f"{area_name}_iptv.txt"

    with open(output_file_name, "w", encoding="utf-8") as output_file:
        output_file.write(f"{area_name}频道,#genre#\n")
        for valid_link in result_set:
            ip = valid_link.split('/')[2].split(':')[0]
            result_content = template_content.replace("ip", f"{ip}:{port}")
            output_file.write(f"{result_content}\n")


def merge_files_and_delete(area_names, movie_file_path):
    # 首先读取电影.txt文件的内容
    movie_content = ""
    if os.path.exists(movie_file_path):
        with open(movie_file_path, "r", encoding="utf-8") as movie_file:
            movie_content = movie_file.read()
    else:
        print(f"文件 {movie_file_path} 不存在，跳过合并。")

    # 开始写入jd.txt文件，首先写入电影.txt的内容
    with open("jd.txt", "w", encoding="utf-8") as jd_file:
        jd_file.write(movie_content)

        # 然后合并其他.txt文件的内容
        for area_name in area_names:
            output_file_name = f"{area_name}_iptv.txt"
            if os.path.exists(output_file_name):
                with open(output_file_name, "r", encoding="utf-8") as output_file:
                    jd_file.write(output_file.read())
                os.remove(output_file_name)  # 删除原始文件
            else:
                print(f"文件 {output_file_name} 不存在，跳过合并。")


def main():
    print("~~~~开始启动扫描程序~~~~")

    # 默认扫描的模板链接
    scan_link1 = "http://{ip}:{port}/hls/1/index.m3u8"
    ip1 = "113.64.147.1"
    port1 = "8811"
    scan_type1 = '1'

    # 新增扫描的模板链接
    scan_link2 = "http://{ip}:{port}/hls/1/index.m3u8"
    ip2 = "42.48.17.204"
    port2 = "808"
    scan_type2 = '1'

    scan_link3 = "http://{ip}:{port}/tsfile/live/1015_1.m3u8"
    ip3 = "119.125.104.139"
    port3 = "9901"
    scan_type3 = '1'

    scan_link4 = "http://{ip}:{port}/newlive/live/hls/2/live.m3u8"
    ip4 = "110.53.52.63"
    port4 = "8888"
    scan_type4 = '1'

    # 生成IP组合并检查链接
    all_ips1 = generate_ip_combinations(ip1, scan_type1)
    links1 = [scan_link1.replace("{ip}", ip).replace("{port}", port1) for ip in all_ips1]

    all_ips2 = generate_ip_combinations(ip2, scan_type2)
    links2 = [scan_link2.replace("{ip}", ip).replace("{port}", port2) for ip in all_ips2]

    all_ips3 = generate_ip_combinations(ip3, scan_type3)
    links3 = [scan_link3.replace("{ip}", ip).replace("{port}", port3) for ip in all_ips3]

    all_ips4 = generate_ip_combinations(ip4, scan_type4)
    links4 = [scan_link4.replace("{ip}", ip).replace("{port}", port4) for ip in all_ips4]

    result_set1 = set()
    result_set2 = set()
    result_set3 = set()
    result_set4 = set()
    progress_counter = [0]
    progress_lock = threading.Lock()
    total_count = len(links1) + len(links2) + len(links3) + len(links4)

    # 多线程检查链接
    threads = []
    for link in links1 + links2 + links3 + links4:
        if link in links1:
            result_set = result_set1
        elif link in links2:
            result_set = result_set2
        elif link in links3:
            result_set = result_set3
        else:
            result_set = result_set4
        thread = threading.Thread(target=check_link,
                                  args=(link, result_set, progress_lock, progress_counter, total_count))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    write_results(result_set1, port1, "地区/揭阳.txt")
    write_results(result_set2, port2, "地区/长沙.txt")
    write_results(result_set3, port3, "地区/梅州.txt")
    write_results(result_set4, port4, "地区/张家界.txt")

    # 电影.txt文件的路径
    movie_file_path = "地区/电影.txt"
    # 合并文件并删除除了电影.txt之外的其他.txt文件
    merge_files_and_delete(["揭阳", "长沙", "梅州", "张家界"], movie_file_path)

    print(f"\n找到揭阳的有效链接ip: {len(result_set1)} 个")
    for link in result_set1:
        ip = link.split('/')[2].split(':')[0]
        print(f"{ip}:{port1}")

    print(f"\n找到湖南的有效链接ip: {len(result_set2)} 个")
    for link in result_set2:
        ip = link.split('/')[2].split(':')[0]
        print(f"{ip}:{port2}")

    print(f"\n找到梅州的有效链接ip: {len(result_set3)} 个")
    for link in result_set3:
        ip = link.split('/')[2].split(':')[0]
        print(f"{ip}:{port3}")

    print(f"\n找到张家界的有效链接ip: {len(result_set4)} 个")
    for link in result_set4:
        ip = link.split('/')[2].split(':')[0]
        print(f"{ip}:{port4}")

    print(f"\n所有的频道列表文件已合并为：jd.txt")


if __name__ == "__main__":
    main()
