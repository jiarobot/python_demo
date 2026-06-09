import numpy as np
import cv2
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import pandas as pd
import matplotlib.pyplot as plt
from scipy import ndimage
from skimage import measure, morphology, segmentation
from sklearn.cluster import KMeans
import json
import geopandas as gpd
from shapely.geometry import Polygon, LineString, Point
import rasterio
from rasterio.features import shapes
import os
from typing import List, Dict, Tuple, Any

class PrecisionMappingSystem:
    """
    高精度视觉测绘系统
    基于传统计算机视觉技术，无需深度学习模型
    """
    
    def __init__(self, ground_resolution: float = 0.1):
        """
        初始化测绘系统
        
        参数:
            ground_resolution: 地面分辨率(米/像素)
        """
        self.ground_resolution = ground_resolution
        self.calibration_params = {}
        
    def camera_calibration(self, calibration_images: List[np.ndarray], 
                          pattern_size: Tuple[int, int] = (9, 6)) -> Dict[str, Any]:
        """
        相机标定 - 获取内参和畸变系数
        
        参数:
            calibration_images: 标定板图像列表
            pattern_size: 棋盘格角点数量
            
        返回:
            相机参数字典
        """
        # 准备对象点 (0,0,0), (1,0,0), (2,0,0) ....,(8,5,0)
        objp = np.zeros((pattern_size[0] * pattern_size[1], 3), np.float32)
        objp[:, :2] = np.mgrid[0:pattern_size[0], 0:pattern_size[1]].T.reshape(-1, 2)
        
        # 存储对象点和图像点
        objpoints = []  # 3D点
        imgpoints = []  # 2D点
        
        for img in calibration_images:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # 查找棋盘格角点
            ret, corners = cv2.findChessboardCorners(gray, pattern_size, None)
            
            if ret:
                objpoints.append(objp)
                
                # 亚像素级角点检测
                criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
                corners_refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
                imgpoints.append(corners_refined)
        
        # 相机标定
        ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None, None)
        
        self.calibration_params = {
            'camera_matrix': mtx,
            'distortion_coeffs': dist,
            'reprojection_error': ret
        }
        
        return self.calibration_params
    
    def orthorectification(self, image: np.ndarray, 
                          dem: np.ndarray = None,
                          camera_height: float = 100.0) -> np.ndarray:
        """
        正射校正 - 消除透视畸变和地形影响
        
        参数:
            image: 输入图像
            dem: 数字高程模型 (可选)
            camera_height: 相机高度(米)
            
        返回:
            正射校正后的图像
        """
        h, w = image.shape[:2]
        
        if dem is None:
            # 如果没有DEM，假设平坦地形
            dem = np.zeros((h, w))
        
        # 简化正射校正过程
        # 在实际应用中，这里需要更复杂的地理变换
        
        # 计算校正变换矩阵
        if self.calibration_params:
            new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(
                self.calibration_params['camera_matrix'],
                self.calibration_params['distortion_coeffs'],
                (w, h), 1, (w, h)
            )
            
            # 去除畸变
            undistorted = cv2.undistort(image, 
                                      self.calibration_params['camera_matrix'],
                                      self.calibration_params['distortion_coeffs'],
                                      None, new_camera_matrix)
            
            # 裁剪图像
            x, y, w_roi, h_roi = roi
            undistorted = undistorted[y:y+h_roi, x:x+w_roi]
            
            return undistorted
        else:
            # 如果没有标定参数，使用简单的仿射变换
            rows, cols = image.shape[:2]
            
            # 定义变换点
            src_points = np.float32([[0, 0], [cols-1, 0], [0, rows-1]])
            dst_points = np.float32([[50, 50], [cols-50, 50], [0, rows-1]])
            
            # 计算仿射变换矩阵
            M = cv2.getAffineTransform(src_points, dst_points)
            ortho_img = cv2.warpAffine(image, M, (cols, rows))
            
            return ortho_img
    
    def feature_extraction(self, image: np.ndarray) -> Dict[str, Any]:
        """
        特征提取 - 检测建筑物、道路等地物特征
        
        参数:
            image: 输入图像
            
        返回:
            包含各种特征的字典
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        features = {}
        
        # 1. 边缘检测
        edges = cv2.Canny(gray, 50, 150)
        features['edges'] = edges
        
        # 2. 角点检测
        corners = cv2.goodFeaturesToTrack(gray, 1000, 0.01, 10)
        features['corners'] = corners
        
        # 3. 线段检测
        lsd = cv2.createLineSegmentDetector(0)
        lines = lsd.detect(gray)[0]
        features['lines'] = lines
        
        # 4. 区域分割
        regions = self._region_segmentation(image)
        features['regions'] = regions
        
        return features
    
    def _region_segmentation(self, image: np.ndarray) -> Dict[str, Any]:
        """
        区域分割 - 使用传统图像分割算法
        
        参数:
            image: 输入图像
            
        返回:
            分割结果
        """
        # 转换为Lab颜色空间进行更好的颜色分割
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        
        # 使用K-means聚类进行分割
        pixel_values = lab.reshape((-1, 3))
        pixel_values = np.float32(pixel_values)
        
        k = 5  # 聚类数量
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
        _, labels, centers = cv2.kmeans(pixel_values, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
        
        # 转换回uint8
        centers = np.uint8(centers)
        segmented_image = centers[labels.flatten()]
        segmented_image = segmented_image.reshape(image.shape)
        
        # 形态学操作优化分割结果
        kernel = np.ones((5, 5), np.uint8)
        segmented_clean = cv2.morphologyEx(segmented_image, cv2.MORPH_CLOSE, kernel)
        segmented_clean = cv2.morphologyEx(segmented_clean, cv2.MORPH_OPEN, kernel)
        
        return {
            'segmented': segmented_image,
            'cleaned': segmented_clean,
            'labels': labels.reshape(image.shape[:2]),
            'centers': centers
        }
    
    def building_detection(self, image: np.ndarray, features: Dict[str, Any]) -> List[Polygon]:
        """
        建筑物检测与轮廓提取
        
        参数:
            image: 输入图像
            features: 特征字典
            
        返回:
            建筑物多边形列表
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # 使用多尺度方法检测建筑物
        buildings = []
        
        # 方法1: 基于边缘和轮廓的方法
        edges = features['edges']
        
        # 形态学操作连接边缘
        kernel = np.ones((3, 3), np.uint8)
        dilated_edges = cv2.dilate(edges, kernel, iterations=2)
        closed_edges = cv2.morphologyEx(dilated_edges, cv2.MORPH_CLOSE, kernel)
        
        # 查找轮廓
        contours, _ = cv2.findContours(closed_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # 过滤小区域
            if area < 1000:  # 最小面积阈值
                continue
            
            # 多边形近似
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # 检查是否为合理的建筑物形状
            if len(approx) >= 4:  # 至少有4个顶点
                # 计算多边形
                polygon_coords = approx.reshape(-1, 2)
                polygon = Polygon(polygon_coords)
                
                # 计算几何特征
                solidity = area / cv2.contourArea(cv2.convexHull(contour))
                extent = area / (cv2.boundingRect(contour)[2] * cv2.boundingRect(contour)[3])
                
                # 基于几何特征过滤
                if solidity > 0.7 and extent > 0.4:
                    buildings.append(polygon)
        
        # 方法2: 基于区域分割的方法
        regions = features['regions']
        labeled_regions = regions['labels']
        
        # 分析每个区域的特征
        unique_labels = np.unique(labeled_regions)
        for label in unique_labels:
            if label == 0:  # 背景
                continue
                
            mask = (labeled_regions == label).astype(np.uint8)
            
            # 计算区域属性
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < 500:
                    continue
                    
                # 多边形近似
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                if len(approx) >= 4:
                    polygon_coords = approx.reshape(-1, 2)
                    polygon = Polygon(polygon_coords)
                    
                    # 检查是否与已有建筑物重叠
                    overlap = False
                    for existing_building in buildings:
                        if polygon.intersects(existing_building):
                            overlap = True
                            break
                    
                    if not overlap:
                        buildings.append(polygon)
        
        return buildings
    
    def road_detection(self, image: np.ndarray, features: Dict[str, Any]) -> List[LineString]:
        """
        道路检测与中心线提取
        
        参数:
            image: 输入图像
            features: 特征字典
            
        返回:
            道路中心线列表
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        roads = []
        
        # 使用线段检测结果
        lines = features['lines']
        
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                
                # 过滤短线段
                if length > 50:  # 最小长度阈值
                    line_obj = LineString([(x1, y1), (x2, y2)])
                    roads.append(line_obj)
        
        # 基于区域分割的道路检测
        regions = features['regions']
        labeled_regions = regions['labels']
        
        # 分析每个区域的形状特征
        unique_labels = np.unique(labeled_regions)
        for label in unique_labels:
            if label == 0:
                continue
                
            mask = (labeled_regions == label).astype(np.uint8)
            
            # 计算区域的骨架(中心线)
            skeleton = morphology.skeletonize(mask)
            
            # 从骨架中提取线段
            skeleton_uint8 = (skeleton * 255).astype(np.uint8)
            lines = cv2.HoughLinesP(skeleton_uint8, 1, np.pi/180, threshold=30, 
                                  minLineLength=20, maxLineGap=10)
            
            if lines is not None:
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    line_obj = LineString([(x1, y1), (x2, y2)])
                    roads.append(line_obj)
        
        return roads
    
    def generate_geojson(self, buildings: List[Polygon], roads: List[LineString], 
                        output_path: str) -> None:
        """
        生成GeoJSON格式的测绘结果
        
        参数:
            buildings: 建筑物多边形列表
            roads: 道路中心线列表
            output_path: 输出文件路径
        """
        # 创建GeoDataFrame
        building_gdf = gpd.GeoDataFrame({
            'id': range(len(buildings)),
            'geometry': buildings,
            'type': ['building'] * len(buildings),
            'area_sq_m': [poly.area * (self.ground_resolution ** 2) for poly in buildings]
        })
        
        road_gdf = gpd.GeoDataFrame({
            'id': range(len(roads)),
            'geometry': roads,
            'type': ['road'] * len(roads),
            'length_m': [line.length * self.ground_resolution for line in roads]
        })
        
        # 合并所有要素
        combined_gdf = gpd.GeoDataFrame(pd.concat([building_gdf, road_gdf], ignore_index=True))
        
        # 设置坐标参考系统 (这里使用伪坐标，实际应用中应使用真实地理坐标)
        combined_gdf.crs = "EPSG:4326"
        
        # 保存为GeoJSON
        combined_gdf.to_file(output_path, driver='GeoJSON')
        
        print(f"测绘结果已保存至: {output_path}")
    
    def create_measurement_report(self, buildings: List[Polygon], 
                                roads: List[LineString]) -> Dict[str, Any]:
        """
        生成测量报告
        
        参数:
            buildings: 建筑物列表
            roads: 道路列表
            
        返回:
            包含详细测量信息的字典
        """
        total_building_area = sum(poly.area for poly in buildings) * (self.ground_resolution ** 2)
        total_road_length = sum(line.length for line in roads) * self.ground_resolution
        
        report = {
            'summary': {
                'total_buildings': len(buildings),
                'total_building_area_sq_m': total_building_area,
                'total_roads': len(roads),
                'total_road_length_m': total_road_length,
                'ground_resolution_m_per_pixel': self.ground_resolution
            },
            'buildings': [
                {
                    'id': i,
                    'area_sq_m': poly.area * (self.ground_resolution ** 2),
                    'perimeter_m': poly.length * self.ground_resolution,
                    'vertices': len(list(poly.exterior.coords)) - 1
                }
                for i, poly in enumerate(buildings)
            ],
            'roads': [
                {
                    'id': i,
                    'length_m': line.length * self.ground_resolution
                }
                for i, line in enumerate(roads)
            ]
        }
        
        return report
    
    def visualize_results(self, image: np.ndarray, buildings: List[Polygon], 
                         roads: List[LineString], output_path: str = None) -> None:
        """
        可视化测绘结果
        
        参数:
            image: 原始图像
            buildings: 建筑物多边形
            roads: 道路中心线
            output_path: 输出图像路径 (可选)
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
        
        # 显示原始图像
        ax1.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        ax1.set_title('原始图像')
        ax1.axis('off')
        
        # 显示检测结果
        ax2.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        
        # 绘制建筑物
        for building in buildings:
            x, y = building.exterior.xy
            ax2.plot(x, y, 'r-', linewidth=2, label='建筑物')
            ax2.fill(x, y, alpha=0.3, color='red')
        
        # 绘制道路
        for road in roads:
            x, y = road.xy
            ax2.plot(x, y, 'b-', linewidth=2, label='道路')
        
        # 避免重复的图例标签
        handles, labels = ax2.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax2.legend(by_label.values(), by_label.keys())
        
        ax2.set_title('测绘结果')
        ax2.axis('off')
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"可视化结果已保存至: {output_path}")
        
        plt.show()

# 示例使用代码
def main():
    """
    主函数 - 演示测绘系统的使用
    """
    # 初始化测绘系统
    mapping_system = PrecisionMappingSystem(ground_resolution=0.1)
    
    # 生成示例航拍图像 (实际应用中应加载真实图像)
    # 这里创建一个模拟的航拍图像
    example_image = generate_example_aerial_image()
    
    # 特征提取
    features = mapping_system.feature_extraction(example_image)
    
    # 建筑物检测
    buildings = mapping_system.building_detection(example_image, features)
    
    # 道路检测
    roads = mapping_system.road_detection(example_image, features)
    
    # 生成GeoJSON
    mapping_system.generate_geojson(buildings, roads, "mapping_results.geojson")
    
    # 生成测量报告
    report = mapping_system.create_measurement_report(buildings, roads)
    print("测量报告:")
    print(json.dumps(report['summary'], indent=2, ensure_ascii=False))
    
    # 可视化结果
    mapping_system.visualize_results(example_image, buildings, roads, "mapping_visualization.png")

def generate_example_aerial_image() -> np.ndarray:
    """
    生成示例航拍图像用于演示
    """
    # 创建一个空白图像
    img = np.ones((800, 1000, 3), dtype=np.uint8) * 200  # 浅灰色背景
    
    # 添加建筑物 (矩形)
    buildings = [
        ((100, 100), (200, 250)),  # (左上角, 右下角)
        ((300, 150), (450, 300)),
        ((600, 200), (750, 350)),
        ((150, 400), (300, 550)),
        ((400, 450), (550, 600)),
        ((650, 500), (800, 650))
    ]
    
    for (x1, y1), (x2, y2) in buildings:
        cv2.rectangle(img, (x1, y1), (x2, y2), (150, 150, 150), -1)  # 灰色建筑物
        cv2.rectangle(img, (x1, y1), (x2, y2), (100, 100, 100), 2)   # 边框
    
    # 添加道路
    roads = [
        ((0, 300), (1000, 300), 30),  # (起点, 终点, 宽度)
        ((500, 0), (500, 800), 25),
        ((200, 400), (800, 400), 20),
        ((700, 100), (700, 700), 15)
    ]
    
    for (x1, y1), (x2, y2), width in roads:
        cv2.line(img, (x1, y1), (x2, y2), (100, 100, 100), width)
    
    # 添加一些噪声和纹理使图像更真实
    noise = np.random.randint(0, 20, img.shape, dtype=np.uint8)
    img = cv2.add(img, noise)
    
    # 添加高斯模糊模拟真实图像
    img = cv2.GaussianBlur(img, (3, 3), 0)
    
    return img

# 确保必要的库已安装
def check_dependencies():
    """
    检查并安装必要的依赖库
    """
    try:
        import cv2
        import matplotlib
        import skimage
        import geopandas
        import rasterio
        import shapely
        print("所有依赖库已安装")
    except ImportError as e:
        print(f"缺少依赖库: {e}")
        print("请使用以下命令安装: pip install opencv-python matplotlib scikit-image geopandas rasterio shapely")

if __name__ == "__main__":
    check_dependencies()
    
    # 在实际应用中，您需要取消注释下面的行并注释掉生成示例图像的部分
    main()
    
    # 由于这是一个演示，我们直接运行示例
    print("由于环境限制，这里只展示代码结构。")
    print("在实际环境中运行前，请确保已安装所有依赖库。")