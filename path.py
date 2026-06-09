import numpy as np
import torch
import torch.nn as nn
import matplotlib.pyplot as plt
from flask import Flask, render_template_string
import json
import threading
import time
import queue
import random
from collections import deque

# 使用线程安全的队列传递状态
state_queue = queue.Queue(maxsize=1)
training_data_queue = queue.Queue(maxsize=1)
training_data_queue.put({'rewards': [], 'training_complete': False})

# ===== 环境定义 =====
class StrategicEnv:
    def __init__(self, size=20, n_agents=5):
        self.size = size
        self.n_agents = n_agents
        self.reset()
        
    def reset(self):
        """重置环境状态"""
        self.grid = np.zeros((self.size, self.size, 4))  # 4种资源层
        self.agent_pos = np.random.randint(0, self.size, (self.n_agents, 2))
        self.threats = []
        self._generate_resources()
        return self._get_global_state()
    
    def _get_global_state(self):
        """获取全局状态"""
        return {
            'grid': self.grid.copy(),
            'agent_pos': self.agent_pos.copy(),
            'threats': self.threats.copy()
        }
    
    def _generate_resources(self):
        """生成资源分布（高斯集群）"""
        for _ in range(8):
            cx, cy = np.random.randint(5, 15, 2)
            for x in range(max(0, cx-3), min(20, cx+4)):
                for y in range(max(0, cy-3), min(20, cy+4)):
                    d = np.sqrt((x-cx)**2 + (y-cy)**2)
                    self.grid[x,y] += np.random.exponential(1/(d+1), 4)
    
    def step(self, actions):
        """执行一步动作"""
        rewards = np.zeros(self.n_agents)
        
        # 1. 移动智能体
        for i, (dx,dy) in enumerate(actions):
            new_x = max(0, min(19, self.agent_pos[i,0] + dx))
            new_y = max(0, min(19, self.agent_pos[i,1] + dy))
            self.agent_pos[i] = [new_x, new_y]
            
            # 2. 收集资源奖励
            rewards[i] += np.sum(self.grid[new_x, new_y]) * 0.2
            self.grid[new_x, new_y] *= 0.8  # 资源消耗
        
        # 3. 动态事件生成
        if np.random.rand() < 0.1:
            threat_x, threat_y = np.random.randint(0, 20, 2)
            self.threats.append([threat_x, threat_y, 10])  # 持续10步
        
        # 4. 威胁处理
        for threat in self.threats[:]:
            threat[2] -= 1
            for i, (ax,ay) in enumerate(self.agent_pos):
                if abs(ax-threat[0]) + abs(ay-threat[1]) < 3:
                    rewards[i] += 2  # 威胁响应奖励
                    threat[2] -= 3
            if threat[2] <= 0:
                self.threats.remove(threat)
                rewards += 1  # 全局奖励
        
        return rewards

# ===== MARL智能体 =====
class PolicyNet(nn.Module):
    def __init__(self, input_dim=25, output_dim=5):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU()
        )
        self.actor = nn.Linear(64, output_dim)  # 动作空间
        self.critic = nn.Linear(64, 1)
        
    def forward(self, x):
        x = self.fc(x)
        action_probs = torch.softmax(self.actor(x), dim=-1)
        state_value = self.critic(x)
        return action_probs, state_value

# 动作空间定义
ACTIONS = [(0,1), (0,-1), (1,0), (-1,0), (0,0)]  # 上、下、右、左、停留

# ===== 简化的训练过程 =====
def train_marl(env, n_episodes=1000):
    agents = [PolicyNet() for _ in range(env.n_agents)]
    optimizers = [torch.optim.Adam(agent.parameters(), lr=0.001) for agent in agents]
    episode_rewards = []
    last_state = None
    
    for ep in range(n_episodes):
        env.reset()
        total_rewards = np.zeros(env.n_agents)
        
        # 将初始状态放入队列
        state_queue.put(env._get_global_state())
        
        for step in range(100):  # 每回合100步
            actions = []
            for i, agent in enumerate(agents):
                # 构建观测（自身位置+资源视图）
                obs = np.concatenate([env.agent_pos[i], env.grid.flatten()[:23]])
                obs = torch.FloatTensor(obs)
                
                probs, _ = agent(obs)
                action = torch.multinomial(probs, 1).item()
                actions.append(ACTIONS[action])
            
            rewards = env.step(actions)
            total_rewards += rewards
            
            # 简化训练：随机梯度下降演示
            for i, agent in enumerate(agents):
                optimizers[i].zero_grad()
                obs = torch.FloatTensor(np.concatenate([env.agent_pos[i], env.grid.flatten()[:23]]))
                _, value = agent(obs)
                loss = -value * rewards[i]  # 简化损失函数
                loss.backward()
                optimizers[i].step()
            
            # 每5步更新一次状态到队列
            if step % 5 == 0:
                state_queue.put(env._get_global_state())
        
        episode_rewards.append(total_rewards.mean())
        print(f"Episode {ep}: Avg Reward = {total_rewards.mean():.2f}")
        
        # 更新训练数据队列
        training_data_queue.put({
            'rewards': episode_rewards.copy(),
            'training_complete': False
        })
        
        # 每100回合生成可视化
        if ep % 100 == 0:
            visualize_strategy(env, ep)
    
    # 训练完成
    training_data_queue.put({
        'rewards': episode_rewards.copy(),
        'training_complete': True
    })
    
    # 绘制训练曲线
    plt.figure(figsize=(10, 5))
    plt.plot(episode_rewards)
    plt.title('MARL Training Performance')
    plt.xlabel('Episode')
    plt.ylabel('Average Reward')
    plt.grid(True)
    plt.savefig('training_curve.png')
    plt.close()
    
    return episode_rewards

# ===== 可视化生成 =====
def visualize_strategy(env, epoch):
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # 绘制资源分布
    resource_img = np.sum(env.grid, axis=2)
    ax.imshow(resource_img.T, cmap='YlOrBr', alpha=0.6)
    
    # 绘制智能体
    for i, (x,y) in enumerate(env.agent_pos):
        ax.scatter(x, y, s=200, marker=f'${i}$', c='blue')
    
    # 绘制威胁
    for x,y,_ in env.threats:
        ax.scatter(x, y, s=300, marker='X', c='red')
    
    ax.set_title(f'Strategic Deployment @ Epoch {epoch}')
    plt.savefig(f'strategy_{epoch}.png')
    plt.close()
    print(f"Saved visualization for epoch {epoch}")

# ===== Web界面 =====
app = Flask(__name__)

def run_training():
    print("Starting training...")
    env = StrategicEnv(size=20, n_agents=5)
    episode_rewards = train_marl(env, n_episodes=500)
    print("Training completed!")

@app.route('/')
def war_room():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
      <title>战略部署沙盘</title>
      <script src="https://d3js.org/d3.v7.min.js"></script>
      <style>
        body { font-family: Arial, sans-serif; }
        #battlefield { border: 2px solid #333; margin: 20px; background-color: #f8f8f8; }
        .agent { fill: blue; opacity: 0.7; stroke: darkblue; stroke-width: 2px; }
        .threat { fill: red; opacity: 0.9; }
        .resource-cell { stroke: #ccc; stroke-width: 0.5px; }
        .panel { display: flex; flex-wrap: wrap; }
        .chart-container { width: 600px; margin-left: 20px; background: white; padding: 10px; border: 1px solid #ddd; }
        .status { background: #e0f7fa; padding: 10px; margin: 10px; border-radius: 5px; }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { text-align: center; padding: 10px; background: #2c3e50; color: white; }
        h2 { border-bottom: 2px solid #2c3e50; padding-bottom: 5px; }
      </style>
    </head>
    <body>
      <div class="header">
        <h1>多智能体战略资源部署系统</h1>
      </div>
      
      <div class="container">
        <div class="status">
          系统状态: <span id="status-text">运行中</span> | 
          训练轮次: <span id="episode-count">0</span> | 
          平均奖励: <span id="avg-reward">0.0</span>
        </div>
        
        <div class="panel">
          <div>
            <h2>实时战略部署视图</h2>
            <svg id="battlefield" width="600" height="600"></svg>
          </div>
          <div class="chart-container">
            <h2>训练曲线</h2>
            <svg id="training-chart" width="550" height="300"></svg>
          </div>
        </div>
      </div>
      
      <script>
        const size = 20;
        const cellSize = 600 / size;
        
        function renderBattlefield(data) {
          const svg = d3.select("#battlefield");
          svg.selectAll("*").remove();
          
          // 绘制资源网格
          for (let x = 0; x < size; x++) {
            for (let y = 0; y < size; y++) {
              // 注意: 这里修正了资源数据的索引顺序
              const resources = data.resources[x][y];
              const resourceValue = resources.reduce((a, b) => a + b, 0);
              const colorIntensity = Math.min(255, 150 + resourceValue * 50);
              
              svg.append("rect")
                .attr("class", "resource-cell")
                .attr("x", x * cellSize)
                .attr("y", y * cellSize)
                .attr("width", cellSize)
                .attr("height", cellSize)
                .style("fill", `rgb(255, ${255 - colorIntensity}, 100)`)
                .style("opacity", 0.3 + resourceValue * 0.1);
            }
          }
          
          // 绘制威胁
          data.threats.forEach(threat => {
            svg.append("rect")
              .attr("class", "threat")
              .attr("x", threat[0] * cellSize)
              .attr("y", threat[1] * cellSize)
              .attr("width", cellSize)
              .attr("height", cellSize)
              .style("fill", "rgba(255, 0, 0, 0.5)");
          });
          
          // 绘制智能体
          data.agents.forEach((pos, i) => {
            const circle = svg.append("circle")
              .attr("class", "agent")
              .attr("cx", pos[0] * cellSize + cellSize/2)
              .attr("cy", pos[1] * cellSize + cellSize/2)
              .attr("r", cellSize/3);
              
            // 添加智能体编号
            svg.append("text")
              .attr("x", pos[0] * cellSize + cellSize/2)
              .attr("y", pos[1] * cellSize + cellSize/2 + 5)
              .attr("text-anchor", "middle")
              .attr("fill", "white")
              .attr("font-weight", "bold")
              .text(i);
          });
        }
        
        function renderTrainingChart(rewards) {
          const svg = d3.select("#training-chart");
          svg.selectAll("*").remove();
          
          if (rewards.length === 0) {
            svg.append("text")
              .attr("x", 275)
              .attr("y", 150)
              .attr("text-anchor", "middle")
              .text("训练数据加载中...");
            return;
          }
          
          const margin = {top: 20, right: 30, bottom: 30, left: 40};
          const width = 550 - margin.left - margin.right;
          const height = 300 - margin.top - margin.bottom;
          
          const x = d3.scaleLinear()
            .domain([0, rewards.length - 1])
            .range([0, width]);
          
          const y = d3.scaleLinear()
            .domain([0, d3.max(rewards)])
            .range([height, 0]);
          
          const line = d3.line()
            .x((d, i) => x(i))
            .y(d => y(d))
            .curve(d3.curveMonotoneX);
          
          const chartSvg = svg.append("g")
            .attr("transform", `translate(${margin.left},${margin.top})`);
          
          // 绘制背景网格
          chartSvg.append("g")
            .attr("class", "grid")
            .attr("transform", `translate(0,${height})`)
            .call(d3.axisBottom(x).ticks(10).tickSize(-height).tickFormat(""));
          
          chartSvg.append("g")
            .attr("class", "grid")
            .call(d3.axisLeft(y).ticks(5).tickSize(-width).tickFormat(""));
          
          // 绘制曲线
          chartSvg.append("path")
            .datum(rewards)
            .attr("fill", "none")
            .attr("stroke", "steelblue")
            .attr("stroke-width", 2)
            .attr("d", line);
          
          // 添加数据点
          chartSvg.selectAll(".dot")
            .data(rewards)
            .enter().append("circle")
            .attr("class", "dot")
            .attr("cx", (d, i) => x(i))
            .attr("cy", d => y(d))
            .attr("r", 3)
            .attr("fill", "steelblue");
          
          // 添加坐标轴
          chartSvg.append("g")
            .attr("transform", `translate(0,${height})`)
            .call(d3.axisBottom(x).ticks(10));
          
          chartSvg.append("g")
            .call(d3.axisLeft(y).ticks(5));
            
          // 添加标题
          chartSvg.append("text")
            .attr("x", width / 2)
            .attr("y", -5)
            .attr("text-anchor", "middle")
            .style("font-size", "14px")
            .text("多智能体强化学习训练曲线");
            
          // 更新状态信息
          if (rewards.length > 0) {
            document.getElementById('episode-count').textContent = rewards.length;
            document.getElementById('avg-reward').textContent = rewards[rewards.length-1].toFixed(2);
          }
        }
        
        // 初始渲染
        function updateVisualization() {
          fetch('/get_state')
            .then(res => res.json())
            .then(data => {
              renderBattlefield(data);
            })
            .catch(err => console.error('Error fetching state:', err));
          
          fetch('/get_training_data')
            .then(res => res.json())
            .then(data => {
              renderTrainingChart(data.rewards);
              if (data.training_complete) {
                document.getElementById('status-text').textContent = "训练完成";
              }
            })
            .catch(err => console.error('Error fetching training data:', err));
        }
        
        // 初始更新
        updateVisualization();
        
        // 每2秒更新视图
        setInterval(updateVisualization, 2000);
      </script>
    </body>
    </html>
    """)

@app.route('/get_state')
def get_state():
    """返回当前战场状态（JSON格式）"""
    try:
        # 从队列获取最新状态，如果队列为空则返回空状态
        if not state_queue.empty():
            state = state_queue.get_nowait()
            state_queue.task_done()
            return json.dumps({
                'agents': state['agent_pos'].tolist(),
                'threats': state['threats'],
                'resources': state['grid'].tolist()
            })
        else:
            # 返回空状态
            return json.dumps({
                'agents': [[0,0]] * 5,
                'threats': [],
                'resources': [[[0,0,0,0]] * 20] * 20
            })
    except Exception as e:
        print(f"Error in get_state: {e}")
        return json.dumps({
            'agents': [[0,0]] * 5,
            'threats': [],
            'resources': [[[0,0,0,0]] * 20] * 20
        })

@app.route('/get_training_data')
def get_training_data():
    """返回训练数据"""
    try:
        if not training_data_queue.empty():
            data = training_data_queue.get_nowait()
            training_data_queue.task_done()
            return json.dumps(data)
        else:
            return json.dumps({'rewards': [], 'training_complete': False})
    except Exception as e:
        print(f"Error in get_training_data: {e}")
        return json.dumps({'rewards': [], 'training_complete': False})

if __name__ == '__main__':
    # 启动训练线程
    training_thread = threading.Thread(target=run_training)
    training_thread.daemon = True
    training_thread.start()
    
    # 初始状态
    state_queue.put({
        'agent_pos': np.zeros((5, 2)).tolist(),
        'threats': [],
        'grid': np.zeros((20, 20, 4)).tolist()
    })
    
    # 启动Web界面
    print("Starting web server at http://localhost:5000")
    app.run(port=5000, debug=False, use_reloader=False)