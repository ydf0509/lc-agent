<template>
  <ToolFileCard :tool-call="toolCall" :collapsed="collapsed" variant="write" />
</template>

<script setup lang="ts">
import type { ToolCall } from '@/stores/chat'
import ToolFileCard from './ToolFileCard.vue'

defineProps<{
  toolCall: ToolCall
  collapsed?: boolean
}>()
</script>
