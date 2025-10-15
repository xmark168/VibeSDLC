<template>
  <div id="app" class="min-h-screen bg-gray-50">
    <!-- Navigation -->
    <AppNavigation />
    
    <!-- Main Content -->
    <main class="container mx-auto px-4 py-8">
      <RouterView />
    </main>
    
    <!-- Toast Container -->
    <div id="toast-container"></div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import AppNavigation from '@/components/AppNavigation.vue'
import { useAuthStore } from '@/stores/auth'

// Initialize auth store
const authStore = useAuthStore()

onMounted(() => {
  // Initialize authentication on app start
  authStore.initializeAuth()
})
</script>

<style>
/* Global styles */
#app {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Custom scrollbar */
::-webkit-scrollbar {
  width: 8px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
}

::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-enter-active,
.slide-leave-active {
  transition: transform 0.3s ease;
}

.slide-enter-from {
  transform: translateX(-100%);
}

.slide-leave-to {
  transform: translateX(100%);
}

/* Loading spinner */
.spinner {
  border: 2px solid #f3f3f3;
  border-top: 2px solid #3498db;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Form styles */
.form-input {
  @apply w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500;
}

.form-label {
  @apply block text-sm font-medium text-gray-700 mb-1;
}

.form-error {
  @apply text-red-600 text-sm mt-1;
}

/* Button styles */
.btn {
  @apply inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed;
}

.btn-primary {
  @apply btn text-white bg-blue-600 hover:bg-blue-700 focus:ring-blue-500;
}

.btn-secondary {
  @apply btn text-gray-700 bg-white border-gray-300 hover:bg-gray-50 focus:ring-blue-500;
}

.btn-danger {
  @apply btn text-white bg-red-600 hover:bg-red-700 focus:ring-red-500;
}

/* Card styles */
.card {
  @apply bg-white shadow rounded-lg;
}

.card-header {
  @apply px-6 py-4 border-b border-gray-200;
}

.card-body {
  @apply px-6 py-4;
}

.card-footer {
  @apply px-6 py-4 border-t border-gray-200 bg-gray-50;
}
</style>
