# 第{{ episode_number }}期：{{ title }}

## 嘉宾介绍

**{{ guest_name }}**
{{ guest_title }}

{{ guest_bio }}

## 本期要点

{{ key_points }}

## 时间轴

{% for item in timeline %}
- [{{ item.time }}] {{ item.topic }}
{% endfor %}

{% if links %}
## 相关链接

{{ links }}
{% endif %}
