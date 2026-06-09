import numpy as np
import cv2
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from scipy import ndimage
from scipy.fftpack import dct, idct
from skimage import filters, morphology, feature
import pywt
from numba import jit
import warnings
warnings.filterwarnings('ignore')

class QuantumInspiredEdgeDetector:
    """量子启发式多尺度边缘检测器"""
    
    def __init__(self):
        self.scales = [1, 2, 4, 8]  # 多尺度参数
        
    def quantum_wavelet_transform(self, image):
        """量子小波变换模拟"""
        coeffs = pywt.wavedec2(image, 'db4', level=3)
        return coeffs
    
    def superposition_edge_detection(self, image):
        """叠加态边缘检测"""
        edges_superposition = np.zeros_like(image, dtype=np.complex64)
        
        for scale in self.scales:
            # 高斯模糊模拟观测效应
            blurred = ndimage.gaussian_filter(image, sigma=scale)
            
            # 多方向梯度计算
            grad_x = ndimage.sobel(blurred, axis=1)
            grad_y = ndimage.sobel(blurred, axis=0)
            
            # 量子幅度计算
            magnitude = np.sqrt(grad_x**2 + grad_y**2)
            phase = np.arctan2(grad_y, grad_x)
            
            # 叠加到主边缘图
            edges_superposition += magnitude * np.exp(1j * phase)
        
        # 坍缩到实数空间
        final_edges = np.abs(edges_superposition)
        return final_edges / np.max(final_edges)

class BioInspiredRetinaProcessor:
    """仿生视网膜处理器"""
    
    def __init__(self):
        self.photoreceptor_kernel = self._create_photoreceptor_kernel()
        self.bipolar_kernel = self._create_bipolar_kernel()
        self.ganglion_kernel = self._create_ganglion_kernel()
    
    def _create_photoreceptor_kernel(self):
        """光感受器层核"""
        return cv2.getGaussianKernel(5, 1.2) * cv2.getGaussianKernel(5, 1.2).T
    
    def _create_bipolar_kernel(self):
        """双极细胞层核 - 中心周边拮抗"""
        # 修复：使用相同尺寸的高斯核
        kernel_size = 15  # 统一使用15x15的尺寸
        
        # 创建中心高斯核（15x15）
        center = cv2.getGaussianKernel(kernel_size, 1.0)
        center = center * center.T
        
        # 创建周边高斯核（15x15）
        surround = cv2.getGaussianKernel(kernel_size, 3.0)
        surround = surround * surround.T
        
        # 调整周边核的权重使其与中心核匹配
        bipolar = center - 0.3 * surround
        
        # 归一化
        bipolar = bipolar / np.sum(np.abs(bipolar))
        return bipolar
    
    def _create_ganglion_kernel(self):
        """神经节细胞层核 - 运动敏感"""
        return np.array([[-1, -1, -1], 
                        [-1, 8, -1], 
                        [-1, -1, -1]], dtype=np.float32)
    
    def process_retinal_layers(self, image):
        """视网膜层次处理"""
        # 光感受器层 - 光适应
        photoreceptor_out = cv2.filter2D(image, -1, self.photoreceptor_kernel)
        
        # 双极细胞层 - 对比度增强
        bipolar_out = cv2.filter2D(photoreceptor_out, -1, self.bipolar_kernel)
        
        # 神经节细胞层 - 特征提取
        ganglion_out = cv2.filter2D(bipolar_out, -1, self.ganglion_kernel)
        
        return {
            'photoreceptor': photoreceptor_out,
            'bipolar': bipolar_out,
            'ganglion': ganglion_out
        }

class FluidDynamicAnalyzer:
    """流体动力学分析器"""
    
    def __init__(self):
        self.viscosity = 0.01  # 动态粘度系数
        
    @jit(nopython=True)
    def navier_stokes_simulation(self, velocity_field, pressure_field, dt=0.1):
        """简化的Navier-Stokes方程模拟"""
        u, v = velocity_field
        p = pressure_field
        
        # 连续性方程
        div_u = np.gradient(u, axis=1) + np.gradient(v, axis=0)
        
        # 动量方程简化
        du_dt = -self.viscosity * (np.gradient(np.gradient(u, axis=1), axis=1) + 
                                 np.gradient(np.gradient(u, axis=0), axis=0))
        dv_dt = -self.viscosity * (np.gradient(np.gradient(v, axis=1), axis=1) + 
                                 np.gradient(np.gradient(v, axis=0), axis=0))
        
        u_new = u + dt * du_dt
        v_new = v + dt * dv_dt
        
        return u_new, v_new, div_u
    
    def analyze_flow_patterns(self, image_sequence):
        """分析图像序列中的流动模式"""
        if len(image_sequence) < 3:
            raise ValueError("需要至少3帧图像进行流体分析")
        
        flow_patterns = []
        for i in range(1, len(image_sequence)):
            # 计算光流
            flow = cv2.calcOpticalFlowFarneback(
                image_sequence[i-1], image_sequence[i], 
                None, 0.5, 3, 15, 3, 5, 1.2, 0
            )
            flow_patterns.append(flow)
        
        return flow_patterns

class PhotonicCrystalMoistureDetector:
    """光子晶体湿度检测器"""
    
    def __init__(self):
        self.moisture_color_profiles = self._initialize_color_profiles()
    
    def _initialize_color_profiles(self):
        """初始化湿度相关的颜色特征"""
        # 基于光子晶体理论的湿度-颜色映射
        profiles = {
            'dry': np.array([0.9, 0.8, 0.7]),  # 干燥区域颜色特征
            'moist': np.array([0.6, 0.7, 0.8]),  # 湿润区域颜色特征
            'wet': np.array([0.4, 0.5, 0.9])   # 积水区域颜色特征
        }
        return profiles
    
    def analyze_moisture_spectrum(self, image):
        """分析湿度光谱特征"""
        # 转换到LAB颜色空间进行更精确的颜色分析
        lab_image = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        
        # 多通道湿度特征提取
        moisture_features = []
        for profile_name, profile in self.moisture_color_profiles.items():
            # 计算颜色相似度
            similarity = self._calculate_color_similarity(lab_image, profile)
            moisture_features.append(similarity)
        
        # 融合多特征
        moisture_map = np.stack(moisture_features, axis=-1)
        return moisture_map
    
    def _calculate_color_similarity(self, lab_image, target_profile):
        """计算颜色相似度"""
        # 修复：正确创建目标颜色样本
        target_bgr = np.uint8([[target_profile * 255]])
        target_lab = cv2.cvtColor(target_bgr, cv2.COLOR_BGR2LAB)
        target_lab = target_lab[0, 0].astype(np.float32)
        
        # 计算颜色距离
        color_distance = np.sqrt(
            np.sum((lab_image.astype(np.float32) - target_lab) ** 2, axis=2)
        )
        
        # 转换为相似度
        similarity = np.exp(-color_distance / 50.0)
        return similarity

class TunnelLeakageDetector:
    """隧道泄露综合检测器"""
    
    def __init__(self):
        self.quantum_edges = QuantumInspiredEdgeDetector()
        self.bio_retina = BioInspiredRetinaProcessor()
        self.fluid_analyzer = FluidDynamicAnalyzer()
        self.moisture_detector = PhotonicCrystalMoistureDetector()
        
        # 泄露特征数据库
        self.leakage_patterns = self._initialize_leakage_patterns()
    
    def _initialize_leakage_patterns(self):
        """初始化泄露模式特征库"""
        patterns = {
            'seepage': {  # 渗水模式
                'edge_density': 0.3,
                'moisture_intensity': 0.7,
                'flow_consistency': 0.8
            },
            'crack_leak': {  # 裂缝泄露
                'edge_density': 0.8,
                'moisture_intensity': 0.6,
                'flow_consistency': 0.4
            },
            'joint_leak': {  # 接缝泄露
                'edge_density': 0.5,
                'moisture_intensity': 0.5,
                'flow_consistency': 0.6
            }
        }
        return patterns
    
    def detect_leakage_comprehensive(self, image_sequence):
        """综合泄露检测"""
        if len(image_sequence) == 0:
            raise ValueError("图像序列不能为空")
        
        results = []
        
        for i, image in enumerate(image_sequence):
            print(f"处理第 {i+1}/{len(image_sequence)} 帧...")
            
            # 确保图像是灰度图
            if len(image.shape) == 3:
                gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray_image = image
            
            # 1. 量子边缘检测
            quantum_edges = self.quantum_edges.superposition_edge_detection(gray_image)
            
            # 2. 仿生视觉处理
            retinal_output = self.bio_retina.process_retinal_layers(gray_image)
            
            # 3. 湿度检测（如果是彩色图像）
            if len(image.shape) == 3:
                moisture_map = self.moisture_detector.analyze_moisture_spectrum(image)
            else:
                # 如果是灰度图，创建伪彩色图用于湿度检测
                color_image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
                moisture_map = self.moisture_detector.analyze_moisture_spectrum(color_image)
            
            # 4. 特征融合与分析
            leakage_probability = self._fuse_features(
                quantum_edges, retinal_output['ganglion'], moisture_map
            )
            
            # 5. 泄露区域定位
            leakage_regions = self._locate_leakage_regions(leakage_probability)
            
            results.append({
                'frame_idx': i,
                'quantum_edges': quantum_edges,
                'retinal_output': retinal_output,
                'moisture_map': moisture_map,
                'leakage_probability': leakage_probability,
                'leakage_regions': leakage_regions
            })
        
        # 6. 时序分析（如果有多帧）
        if len(image_sequence) > 1:
            temporal_analysis = self._temporal_analysis(results)
            results.append({'temporal_analysis': temporal_analysis})
        
        return results
    
    def _fuse_features(self, quantum_edges, ganglion_output, moisture_map):
        """多特征融合"""
        # 边缘特征权重
        edge_weight = 0.4
        # 运动/变化特征权重
        motion_weight = 0.3
        # 湿度特征权重
        moisture_weight = 0.3
        
        # 特征归一化
        edges_norm = quantum_edges / (np.max(quantum_edges) + 1e-8)
        motion_norm = ganglion_output / (np.max(np.abs(ganglion_output)) + 1e-8)
        moisture_norm = np.mean(moisture_map, axis=2)
        moisture_norm = moisture_norm / (np.max(moisture_norm) + 1e-8)
        
        # 加权融合
        fused_probability = (
            edge_weight * edges_norm +
            motion_weight * motion_norm +
            moisture_weight * moisture_norm
        )
        
        return fused_probability
    
    def _locate_leakage_regions(self, probability_map, threshold=0.6):
        """定位泄露区域"""
        # 二值化
        binary_map = probability_map > threshold
        
        # 形态学操作
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        cleaned_map = morphology.closing(binary_map, kernel)
        
        # 连通区域分析
        labeled_array, num_features = ndimage.label(cleaned_map)
        
        regions = []
        for i in range(1, num_features + 1):
            region_mask = labeled_array == i
            if np.sum(region_mask) > 50:  # 过滤小区域
                regions.append(region_mask)
        
        return regions
    
    def _temporal_analysis(self, results):
        """时序一致性分析"""
        if len(results) < 2:
            return None
        
        # 分析泄露区域的时序稳定性
        stability_scores = []
        for i in range(len(results) - 1):
            current_regions = results[i]['leakage_regions']
            next_regions = results[i + 1]['leakage_regions']
            
            # 计算区域重叠度作为稳定性指标
            stability = self._calculate_region_stability(
                current_regions, next_regions
            )
            stability_scores.append(stability)
        
        return np.mean(stability_scores)
    
    def _calculate_region_stability(self, regions1, regions2):
        """计算区域稳定性"""
        if not regions1 or not regions2:
            return 0.0
        
        max_overlap = 0.0
        for r1 in regions1:
            for r2 in regions2:
                # 修复：确保区域是布尔数组
                r1_bool = r1.astype(bool)
                r2_bool = r2.astype(bool)
                
                intersection = np.sum(r1_bool & r2_bool)
                union = np.sum(r1_bool | r2_bool)
                
                if union > 0:
                    overlap = intersection / union
                    max_overlap = max(max_overlap, overlap)
        
        return max_overlap

# 使用示例和测试代码
def main():
    # 模拟隧道图像数据（实际应用中替换为真实图像）
    print("初始化隧道泄露检测系统...")
    detector = TunnelLeakageDetector()
    
    # 生成测试图像序列
    test_sequence = []
    for i in range(3):
        # 创建模拟隧道图像
        test_image = np.random.randint(50, 150, (480, 640, 3), dtype=np.uint8)
        
        # 添加模拟泄露区域
        cv2.circle(test_image, (320, 240), 30, (100, 150, 200), -1)  # 湿润区域
        cv2.line(test_image, (200, 100), (250, 150), (80, 120, 180), 5)  # 裂缝
        
        test_sequence.append(test_image)
    
    print("开始泄露检测分析...")
    # 执行检测
    results = detector.detect_leakage_comprehensive(test_sequence)
    
    # 可视化结果
    visualize_results(results, test_sequence)

def visualize_results(results, original_images):
    """可视化检测结果"""
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    
    for i, result in enumerate(results[:3]):  # 显示前三帧结果
        if 'frame_idx' in result:
            # 原始图像
            axes[0, i].imshow(cv2.cvtColor(original_images[i], cv2.COLOR_BGR2RGB))
            axes[0, i].set_title(f'原始图像 Frame {i+1}')
            axes[0, i].axis('off')
            
            # 泄露概率图
            prob_map = axes[1, i].imshow(result['leakage_probability'], cmap='jet')
            axes[1, i].set_title(f'泄露概率图 Frame {i+1}')
            axes[1, i].axis('off')
            plt.colorbar(prob_map, ax=axes[1, i])
    
    plt.tight_layout()
    plt.savefig('tunnel_leakage_detection_results.png', dpi=300, bbox_inches='tight')
    plt.show()

# C++部署准备接口
class CppExportable:
    """为C++部署准备的接口类"""
    
    @staticmethod
    def prepare_for_cpp_export(detector):
        """准备C++部署所需的数据结构"""
        export_data = {
            'quantum_scales': detector.quantum_edges.scales,
            'retina_kernels': {
                'photoreceptor': detector.bio_retina.photoreceptor_kernel.tolist(),
                'bipolar': detector.bio_retina.bipolar_kernel.tolist(),
                'ganglion': detector.bio_retina.ganglion_kernel.tolist()
            },
            'fluid_params': {
                'viscosity': detector.fluid_analyzer.viscosity
            },
            'leakage_patterns': detector.leakage_patterns
        }
        return export_data

if __name__ == "__main__":
    main()
    
    # 生成C++部署配置
    detector = TunnelLeakageDetector()
    cpp_config = CppExportable.prepare_for_cpp_export(detector)
    print("C++部署配置已生成")