<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span style="font-size:16px;font-weight:600">拔河/对抗成绩录入</span>
          <el-select v-model="filterEvent" placeholder="选择对抗项目" style="width:220px" @change="loadTeams">
            <el-option v-for="e in confrontEvents" :key="e.id" :label="e.name" :value="e.id" />
          </el-select>
        </div>
      </template>

      <div v-if="currentEvent" class="event-info">
        <el-tag>{{ currentEvent.name }}</el-tag>
        <el-tag type="warning">{{ currentEvent.confrontation_format === 'bo5' ? '五局三胜' : '三局两胜' }}</el-tag>
        <el-tag type="info">共 {{ teams.length }} 支队伍</el-tag>
      </div>

      <!-- 比赛对阵设置 -->
      <el-row :gutter="20" style="margin-top:20px" v-if="teams.length >= 2">
        <el-col :span="12">
          <el-card shadow="never" class="match-card">
            <template #header>
              <div style="display:flex;justify-content:space-between;align-items:center">
                <span>设置对阵</span>
                <el-button type="primary" size="small" @click="createMatch">开始比赛</el-button>
              </div>
            </template>
            <el-form label-width="70px">
              <el-form-item label="队伍A">
                <el-select v-model="matchForm.teamA" style="width:100%">
                  <el-option v-for="t in teams" :key="t.id" :label="t.class_name" :value="t.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="队伍B">
                <el-select v-model="matchForm.teamB" style="width:100%">
                  <el-option v-for="t in teams" :key="t.id" :label="t.class_name" :value="t.id" />
                </el-select>
              </el-form-item>
            </el-form>
          </el-card>
        </el-col>

        <!-- 当前对战局次录入 -->
        <el-col :span="12" v-if="currentMatch">
          <el-card shadow="never" class="match-card">
            <template #header>
              <span>{{ teamName(currentMatch.teamA) }} VS {{ teamName(currentMatch.teamB) }}</span>
            </template>
            <div class="rounds">
              <div v-for="(round, idx) in currentMatch.rounds" :key="idx" class="round-item">
                <span class="round-label">第{{ idx + 1 }}局：</span>
                <el-radio-group v-model="round.winner" size="small">
                  <el-radio-button :label="currentMatch.teamA">{{ teamName(currentMatch.teamA) }}</el-radio-button>
                  <el-radio-button :label="currentMatch.teamB">{{ teamName(currentMatch.teamB) }}</el-radio-button>
                </el-radio-group>
              </div>
            </div>
            <div class="match-result" v-if="matchWinner">
              <el-alert :title="`比赛结果：${teamName(matchWinner)} 获胜`" type="success" :closable="false" />
            </div>
            <div style="margin-top:16px;display:flex;gap:8px">
              <el-button type="primary" @click="submitMatch" :loading="submitting">提交比赛结果</el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 已录入成绩 -->
      <el-card shadow="never" style="margin-top:20px" v-if="teamScores.length">
        <template #header><span>已录入成绩</span></template>
        <el-table :data="teamScores" size="small">
          <el-table-column prop="rank" label="名次" width="80" align="center">
            <template #default="{ row }">{{ row.rank ? `第${row.rank}名` : '-' }}</template>
          </el-table-column>
          <el-table-column prop="class_name" label="班级" min-width="120" />
          <el-table-column prop="result" label="成绩" width="120" align="center" />
          <el-table-column prop="points" label="积分" width="80" align="center" />
        </el-table>
      </el-card>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { eventApi, teamRegistrationApi, teamScoreApi } from '@/api'

const confrontEvents = ref([])
const teams = ref([])
const teamScores = ref([])
const filterEvent = ref('')
const submitting = ref(false)

const currentEvent = computed(() => confrontEvents.value.find(e => e.id == filterEvent.value))

const matchForm = reactive({ teamA: '', teamB: '' })
const currentMatch = ref(null)

const maxRounds = computed(() => {
  return currentEvent.value?.confrontation_format === 'bo5' ? 5 : 3
})

const matchWinner = computed(() => {
  if (!currentMatch.value) return null
  const rounds = currentMatch.value.rounds
  const winsA = rounds.filter(r => r.winner === currentMatch.value.teamA).length
  const winsB = rounds.filter(r => r.winner === currentMatch.value.teamB).length
  const needed = maxRounds.value === 5 ? 3 : 2
  if (winsA >= needed) return currentMatch.value.teamA
  if (winsB >= needed) return currentMatch.value.teamB
  return null
})

const teamName = id => teams.value.find(t => t.id === id)?.class_name || id

async function loadTeams() {
  if (!filterEvent.value) return
  const res = await teamRegistrationApi.list({ event: filterEvent.value, page_size: 200 })
  teams.value = res.results || res
  const scRes = await teamScoreApi.list({ event: filterEvent.value, page_size: 200 })
  teamScores.value = scRes.results || scRes
}

function createMatch() {
  if (matchForm.teamA === matchForm.teamB) {
    ElMessage.warning('请选择不同的队伍')
    return
  }
  currentMatch.value = {
    teamA: matchForm.teamA,
    teamB: matchForm.teamB,
    rounds: Array.from({ length: maxRounds.value }, (_, i) => ({ number: i + 1, winner: '' }))
  }
}

async function submitMatch() {
  if (!matchWinner.value) {
    ElMessage.warning('比赛尚未分出胜负，请继续录入')
    return
  }
  submitting.value = true
  try {
    const match = currentMatch.value
    const loserTeamId = match.teamA === matchWinner.value ? match.teamB : match.teamA
    const winsW = match.rounds.filter(r => r.winner === matchWinner.value).length
    const winsL = match.rounds.filter(r => r.winner === loserTeamId).length

    // 构建轮次数据（所有已填写的局）
    const winnerRounds = match.rounds
      .filter(r => r.winner === matchWinner.value)
      .map(r => ({ round_number: r.number, winner_class: teamName(matchWinner.value) }))
    const loserRounds = match.rounds
      .filter(r => r.winner === loserTeamId)
      .map(r => ({ round_number: r.number, winner_class: teamName(loserTeamId) }))

    // 提交胜者成绩（upsert）
    const existingScores = teamScores.value
    const existingWinner = existingScores.find(s => s.team_registration === matchWinner.value)
    if (existingWinner) {
      await teamScoreApi.update(existingWinner.id, {
        result: `${winsW}:${winsL}（胜）`,
        result_numeric: winsW,
      })
    } else {
      await teamScoreApi.create({
        team_registration: matchWinner.value,
        stage: 'final',
        result: `${winsW}:${winsL}（胜）`,
        result_numeric: winsW,
        rounds_data: winnerRounds,
      })
    }

    // 提交负者成绩（upsert）
    const existingLoser = existingScores.find(s => s.team_registration === loserTeamId)
    if (existingLoser) {
      await teamScoreApi.update(existingLoser.id, {
        result: `${winsL}:${winsW}（负）`,
        result_numeric: winsL,
      })
    } else {
      await teamScoreApi.create({
        team_registration: loserTeamId,
        stage: 'final',
        result: `${winsL}:${winsW}（负）`,
        result_numeric: winsL,
        rounds_data: loserRounds,
      })
    }

    ElMessage.success(`比赛结果已保存：${teamName(matchWinner.value)} 获胜`)
    currentMatch.value = null
    loadTeams()
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  const res = await eventApi.list({ page_size: 200 })
  confrontEvents.value = (res.results || res).filter(e => e.event_type === 'team_confrontation')
})
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.event-info { display: flex; gap: 8px; margin-bottom: 8px; }
.match-card { height: 100%; }
.rounds { display: flex; flex-direction: column; gap: 12px; }
.round-item { display: flex; align-items: center; gap: 12px; }
.round-label { width: 60px; font-weight: 600; }
.match-result { margin-top: 16px; }
</style>
