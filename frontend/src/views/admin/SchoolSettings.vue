<template>
  <el-card shadow="never" v-loading="loading">
    <template #header><h2 class="settings-heading">学校设置</h2></template>
    <el-alert title="学校名称用于登录页和新建运动会。班级设置不会重命名已有学生、报名或历届记录。" type="info" :closable="false" />
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="settings-form" @submit.prevent="save">
      <el-form-item label="学校名称" prop="school_name"><el-input v-model="form.school_name" maxlength="100" /></el-form-item>
      <el-form-item label="系统名称" prop="system_name"><el-input v-model="form.system_name" maxlength="50" /></el-form-item>
      <el-form-item label="班级与年级" :error="classError">
        <el-input v-model="classText" type="textarea" :rows="12" aria-label="班级与年级，每行一条" placeholder="每行填写：班级名称 | 年级名称&#10;高一1班 | 高一&#10;高一2班 | 高一&#10;小学一年级1班 | 小学一年级" />
        <p class="form-help">每行一个班级，用半角竖线 | 分隔。支持小学、初中、高中和自定义名称，最多 2000 个班级。</p>
      </el-form-item>
      <el-button type="primary" native-type="submit" :loading="saving" :disabled="!ready">保存设置</el-button>
    </el-form>
  </el-card>
</template>
<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/api/request'
import { useSchoolStore } from '@/stores/school'
import { parseSchoolClasses } from '@/utils/schoolDirectory'
const school = useSchoolStore()
const form = reactive({ school_name: '', system_name: 'CampusSport' })
const formRef = ref()
const classText = ref('')
const classError = ref('')
const loading = ref(true)
const ready = ref(false)
const saving = ref(false)
const rules = {
  school_name: [{ required: true, whitespace: true, message: '请输入学校名称', trigger: 'blur' }],
  system_name: [{ required: true, whitespace: true, message: '请输入系统名称', trigger: 'blur' }]
}
onMounted(async () => {
  try {
    const data = await request.get('/school/profile/')
    Object.assign(form, { school_name: data.school_name, system_name: data.system_name })
    classText.value = data.classes.map(item => `${item.name} | ${item.grade}`).join('\n')
    ready.value = true
  } finally { loading.value = false }
})
async function save() {
  if (saving.value || !ready.value) return
  classError.value = ''
  if (!await formRef.value.validate().catch(() => false)) return
  let classes
  try { classes = parseSchoolClasses(classText.value) }
  catch (error) { classError.value = error.message; return }
  saving.value = true
  try {
    await request.patch('/school/profile/', { ...form, classes })
    ElMessage.success('学校设置已保存')
    await Promise.all([school.loadBranding(), school.loadDirectory()])
  } finally { saving.value = false }
}
</script>
<style scoped>
.settings-heading { margin: 0; font-size: 18px; }
.settings-form { max-width: 680px; margin-top: 24px; }
.form-help { margin: 8px 0 0; color: #606266; line-height: 1.6; }
</style>
