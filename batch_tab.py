# 翡翠珠宝镶嵌托设计AI辅助系统 - 默认配置
app:
  name: 翡翠珠宝镶嵌托设计AI辅助系统
  version: "1.0.0"
  theme: dark
  language: zh_CN

sd_webui:
  api_url: "http://127.0.0.1:7860"
  api_mode: a1111
  timeout: 120
  default_sampler: "DPM++ 2M Karras"
  default_steps: 30
  default_cfg_scale: 7.0
  default_width: 512
  default_height: 512
  default_batch_size: 1
  hires_fix_enabled: false
  hires_fix_upscaler: "4x-UltraSharp"
  hires_fix_scale: 2.0
  adetailer_enabled: false

mimo_api:
  api_key: ""
  base_url: "https://api.xiaomimimo.com/v1"
  model: "mimo-v2-flash"
  timeout: 60
  max_retries: 3

training:
  default_network_type: LoRA
  default_rank: 32
  default_learning_rate_unet: 0.0001
  default_learning_rate_te: 0.00005
  default_epochs: 10
  default_batch_size: 1
  default_resolution: 512
  default_optimizer: AdamW8bit
  default_mixed_precision: fp16
  save_format: safetensors
  save_every_n_steps: 500
  preview_every_n_steps: 100
  kohya_ss_path: ""

crawler:
  concurrent_requests: 3
  request_interval_min: 2.0
  request_interval_max: 5.0
  min_resolution_width: 800
  min_resolution_height: 600
  similarity_threshold: 60
  max_images_per_site: 100
  proxy_enabled: false
  proxy_type: http
  proxy_url: ""
  user_agent_rotation: true

gallery:
  thumbnail_size: 256
  default_sort: time_desc

batch:
  max_concurrent: 4
