<template>
  <div class="note-card">
    <div class="note-header">
      <span class="note-author">{{ note.author }}</span>
      <span class="note-time">{{ timeAgo(note.created_at) }}</span>
    </div>
    <p class="note-content">{{ note.content }}</p>

    <div class="reactions">
      <button
        v-for="emoji in EMOJIS"
        :key="emoji"
        class="reaction-btn"
        :class="{ active: getCount(emoji) > 0 }"
        @click="$emit('react', { noteId: note.id, emoji })"
        :title="`React with ${emoji}`"
      >
        {{ emoji }}
        <span v-if="getCount(emoji) > 0" class="reaction-count">{{ getCount(emoji) }}</span>
      </button>
    </div>

    <button class="delete-btn" @click="confirmDelete" title="Delete note">✕</button>
  </div>
</template>

<script setup>
const EMOJIS = ['👍', '❤️', '😂', '😮', '😢', '👏', '🔥', '🎉']

const props = defineProps({
  note: { type: Object, required: true },
})

const emit = defineEmits(['react', 'delete'])

function getCount(emoji) {
  return props.note.reactions.find(r => r.emoji === emoji)?.count ?? 0
}

function confirmDelete() {
  if (confirm('Delete this note?')) emit('delete', props.note.id)
}

function timeAgo(isoString) {
  const diff = (Date.now() - new Date(isoString).getTime()) / 1000
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}
</script>

<style scoped>
.note-card {
  background: #fff;
  border-radius: 12px;
  padding: 18px;
  box-shadow: 0 1px 4px rgba(0,0,0,.08);
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: box-shadow .15s;
}

.note-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,.12); }

.note-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.note-author {
  font-weight: 700;
  font-size: 0.9rem;
  color: #4f6ef7;
}

.note-time {
  font-size: 0.78rem;
  color: #aaa;
  margin-left: auto;
}

.note-content {
  font-size: 0.95rem;
  line-height: 1.55;
  color: #333;
  white-space: pre-wrap;
  word-break: break-word;
  flex: 1;
}

.reactions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}

.reaction-btn {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  background: #f5f5f5;
  border: 1px solid transparent;
  border-radius: 20px;
  padding: 4px 9px;
  font-size: 1rem;
  cursor: pointer;
  transition: background .12s, border-color .12s, transform .1s;
  line-height: 1;
}

.reaction-btn:hover {
  background: #eef1ff;
  border-color: #c5cef7;
  transform: scale(1.1);
}

.reaction-btn.active {
  background: #eef1ff;
  border-color: #4f6ef7;
}

.reaction-count {
  font-size: 0.78rem;
  font-weight: 600;
  color: #4f6ef7;
}

.delete-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  background: none;
  border: none;
  color: #ccc;
  font-size: 0.8rem;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: color .12s, background .12s;
  line-height: 1;
}

.delete-btn:hover {
  color: #e74c3c;
  background: #fff0f0;
}
</style>
