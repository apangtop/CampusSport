<template>
  <div>
    <el-page-header content="导出报告" @back="$router.push(`/admin/meets/${meetId}`)" style="margin-bottom:20px" />
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card shadow="never" class="report-card">
          <div class="report-icon">📋</div>
          <h3>秩序册</h3>
          <p>包含封面、目录、赛程总览、各项目参赛名单及积分规则</p>
          <el-tag type="primary" size="small">Word (.docx) 格式</el-tag>
          <div class="report-features">
            <span>✓ 封面页</span>
            <span>✓ 目录</span>
            <span>✓ 赛程总览表</span>
            <span>✓ 各项目参赛名单</span>
            <span>✓ 积分规则</span>
          </div>
          <div style="margin-top:20px">
            <el-button type="primary" size="large" :loading="loadingOrder" @click="downloadOrderBook">
              <el-icon><Download /></el-icon> 下载秩序册 (Word)
            </el-button>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" class="report-card">
          <div class="report-icon">🏆</div>
          <h3>成绩报表</h3>
          <p>包含班级总积分榜和各项目详细成绩单</p>
          <el-tag type="warning" size="small">Excel (.xlsx) 格式</el-tag>
          <div class="report-features">
            <span>✓ 班级积分总榜</span>
            <span>✓ 各项目成绩明细</span>
          </div>
          <div style="margin-top:20px">
            <el-button type="warning" size="large" :loading="loadingResult" @click="downloadResultReport">
              <el-icon><Download /></el-icon> 下载成绩报表 (Excel)
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const route = useRoute()
const meetId = route.params.id
const loadingOrder = ref(false)
const loadingResult = ref(false)

async function downloadFile(url, filename, mimeType, loadingRef) {
  loadingRef.value = true
  try {
    const token = localStorage.getItem('access_token')
    const res = await axios.get(url, {
      headers: { Authorization: `Bearer ${token}` },
      responseType: 'blob'
    })
    const blob = new Blob([res.data], { type: mimeType })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(link.href)
    ElMessage.success('下载成功')
  } catch {
    ElMessage.error('下载失败，请重试')
  } finally {
    loadingRef.value = false
  }
}

function downloadOrderBook() {
  downloadFile(
    `/api/reports/generate_order_book/?sports_meet_id=${meetId}`,
    '秩序册.docx',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    loadingOrder
  )
}

function downloadResultReport() {
  downloadFile(
    `/api/reports/generate_result_report/?sports_meet_id=${meetId}`,
    '成绩报表.xlsx',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    loadingResult
  )
}
</script>

<style scoped>
.report-card { text-align: center; padding: 20px 0; }
.report-icon { font-size: 64px; margin-bottom: 12px; }
.report-card h3 { font-size: 20px; margin: 0 0 8px; }
.report-card p { color: #888; font-size: 14px; margin: 0 0 12px; }
.report-features {
  display: flex; flex-direction: column; gap: 4px;
  margin: 12px auto; max-width: 200px; text-align: left;
  font-size: 13px; color: #67c23a;
}
</style>
