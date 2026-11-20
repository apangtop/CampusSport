<template>
  <router-view />
</template>
<script setup>
import { onMounted } from 'vue'
import { useSchoolStore } from '@/stores/school'
const school = useSchoolStore()
onMounted(() => school.loadBranding().catch(() => {}))
</script>
