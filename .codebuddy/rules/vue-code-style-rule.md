# Vue 代码规范

> 基于 Tencent Code Guide 和 Vue 官方风格指南整理

## 目录

1. [命名规范](#命名规范)
2. [目录结构](#目录结构)
3. [组件规范](#组件规范)
4. [模板规范](#模板规范)
5. [脚本规范](#脚本规范)
6. [样式规范](#样式规范)
7. [状态管理](#状态管理)
8. [TypeScript 规范](#typescript-规范)
9. [性能优化](#性能优化)
10. [安全规范](#安全规范)

---

## 命名规范

### 文件命名

```
// Component files - PascalCase
components/
├── UserProfile.vue
├── SearchInput.vue
└── NavBar.vue

// Composables - camelCase with 'use' prefix
composables/
├── useAuth.ts
├── useFetch.ts
└── useLocalStorage.ts

// Views/Pages - PascalCase or kebab-case
views/
├── Home.vue
├── UserProfile.vue
└── settings/
    └── AccountSettings.vue

// Utils - camelCase
utils/
├── formatDate.ts
├── httpClient.ts
└── validators.ts

// Constants - UPPER_SNAKE_CASE
constants/
├── API_ENDPOINTS.ts
└── ERROR_CODES.ts
```

### 组件命名

```vue
<!-- GOOD: Multi-word component names -->
<script setup lang="ts">
// Component definition
</script>

<template>
  <!-- Always use multi-word names -->
  <UserProfile />
  <SearchInput />
  <NavigationMenu />
</template>

<!-- BAD: Single-word names -->
<User />
<Input />
<Menu />
```

### Prop 命名

```typescript
// GOOD: camelCase in declaration, kebab-case in template
defineProps<{
  isVisible: boolean;
  userName: string;
  itemCount: number;
  apiEndpoint: string;
}>();

// Template usage
<!-- <user-profile :is-visible="true" :user-name="name" /> -->
```

### 事件命名

```typescript
// GOOD: kebab-case with verb-noun pattern
const emit = defineEmits<{
  'update:modelValue': [value: string];
  'item-selected': [item: Item];
  'form-submitted': [data: FormData];
  'modal-closed': [];
}>();

// BAD
const emit = defineEmits<{
  'updateModelValue': [value: string];  // Should be kebab-case
  'select': [item: Item];               // Too vague
  'submit': [data: FormData];           // Missing context
}>();
```

---

## 目录结构

### 标准项目结构

```
src/
├── api/                    # API 请求封装
│   ├── modules/           # 按业务模块划分
│   │   ├── user.ts
│   │   └── product.ts
│   ├── interceptors.ts    # 请求/响应拦截器
│   └── index.ts           # axios 实例配置
│
├── assets/                 # 静态资源
│   ├── images/
│   ├── fonts/
│   └── styles/
│       ├── variables.scss
│       ├── mixins.scss
│       └── global.scss
│
├── components/             # 通用组件
│   ├── common/            # 基础组件
│   │   ├── Button/
│   │   │   ├── Button.vue
│   │   │   ├── Button.types.ts
│   │   │   └── index.ts
│   │   └── Input/
│   ├── layout/            # 布局组件
│   └── business/          # 业务组件
│
├── composables/            # 组合式函数
│   ├── useAuth.ts
│   ├── useFetch.ts
│   └── usePermission.ts
│
├── constants/              # 常量定义
│   ├── app.ts
│   └── routes.ts
│
├── directives/             # 自定义指令
│   ├── clickOutside.ts
│   └── permission.ts
│
├── hooks/                  # 钩子函数（与 composables 二选一）
│
├── plugins/                # 插件
│   └── i18n.ts
│
├── router/                 # 路由配置
│   ├── modules/           # 路由模块
│   ├── guards.ts          # 路由守卫
│   └── index.ts
│
├── stores/                 # Pinia 状态管理
│   ├── modules/
│   │   ├── user.ts
│   │   └── app.ts
│   └── index.ts
│
├── types/                  # TypeScript 类型定义
│   ├── api.d.ts
│   ├── global.d.ts
│   └── models/
│
├── utils/                  # 工具函数
│   ├── format.ts
│   ├── storage.ts
│   └── validate.ts
│
├── views/                  # 页面组件
│   ├── home/
│   │   ├── Home.vue
│   │   ├── components/    # 页面专属组件
│   │   └── composables/   # 页面专属组合式函数
│   └── user/
│
├── App.vue
└── main.ts
```

### 组件目录结构

```
components/
├── Button/
│   ├── Button.vue          # 组件主文件
│   ├── Button.types.ts     # 类型定义
│   ├── Button.test.ts      # 单元测试
│   ├── Button.stories.ts   # Storybook (可选)
│   └── index.ts            # 导出
```

---

## 组件规范

### 组件定义

```vue
<!-- GOOD: Use <script setup> with TypeScript -->
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import type { User } from '@/types';

// Props with type definition
const props = defineProps<{
  user: User;
  isVisible?: boolean;
}>();

// Emits with type definition
const emit = defineEmits<{
  'update:user': [user: User];
  'close': [];
}>();

// Reactive state
const isLoading = ref(false);
const localUser = ref({ ...props.user });

// Computed properties
const displayName = computed(() => {
  return `${localUser.value.firstName} ${localUser.value.lastName}`;
});

// Methods
const handleSubmit = async () => {
  isLoading.value = true;
  try {
    emit('update:user', localUser.value);
  } finally {
    isLoading.value = false;
  }
};

// Lifecycle hooks
onMounted(() => {
  console.log('Component mounted');
});
</script>

<template>
  <div v-if="isVisible" class="user-card">
    <span>{{ displayName }}</span>
    <button @click="handleSubmit" :disabled="isLoading">
      Submit
    </button>
  </div>
</template>

<style scoped lang="scss">
.user-card {
  padding: 16px;
}
</style>
```

### 组件拆分原则

```typescript
// GOOD: Single Responsibility
// UserProfileCard.vue - Only handles user profile display
// UserAvatar.vue - Only handles avatar rendering
// UserStats.vue - Only handles stats display

// BAD: God Component
// UserDashboard.vue - Handles everything (profile, stats, settings, notifications...)
```

### Props 默认值

```typescript
// GOOD: Use withDefaults for optional props
const props = withDefaults(
  defineProps<{
    size?: 'small' | 'medium' | 'large';
    disabled?: boolean;
    loading?: boolean;
  }>(),
  {
    size: 'medium',
    disabled: false,
    loading: false,
  }
);

// Alternative: Runtime defaults
const props = defineProps({
  size: {
    type: String as PropType<'small' | 'medium' | 'large'>,
    default: 'medium',
    validator: (value: string) => ['small', 'medium', 'large'].includes(value),
  },
});
```

---

## 模板规范

### 指令顺序

```vue
<!-- GOOD: Follow Vue recommended order -->
<template>
  <div
    v-if="isVisible"
    v-show="shouldShow"
    v-for="item in items"
    :key="item.id"
    v-model="value"
    ref="container"
    class="container"
    :class="{ active: isActive }"
    :style="{ color: textColor }"
    @click="handleClick"
    @keyup.enter="handleEnter"
    v-slot="slotProps"
  >
    {{ item.name }}
  </div>
</template>

<!-- 
  Order: 
  1. v-if, v-else-if, v-else, v-show
  2. v-for
  3. v-model
  4. ref
  5. id
  6. class
  7. :class
  8. style, :style
  9. Other attributes
  10. Events (@click, etc.)
  11. v-slot
-->
```

### 插值表达式

```vue
<!-- GOOD: Simple expressions -->
<template>
  <span>{{ user.name }}</span>
  <span>{{ formatDate(date) }}</span>
  <span>{{ count + 1 }}</span>
</template>

<!-- BAD: Complex logic in template -->
<template>
  <span>{{ user.firstName + ' ' + user.lastName + ' (' + user.age + ' years)' }}</span>
</template>

<!-- GOOD: Use computed or method instead -->
<script setup lang="ts">
const displayInfo = computed(() => {
  return `${user.value.firstName} ${user.value.lastName} (${user.value.age} years)`;
});
</script>

<template>
  <span>{{ displayInfo }}</span>
</template>
```

### v-for 规范

```vue
<!-- GOOD: Always use :key with meaningful value -->
<template>
  <li v-for="item in items" :key="item.id">
    {{ item.name }}
  </li>
</template>

<!-- BAD: Using index as key (unless necessary) -->
<template>
  <li v-for="(item, index) in items" :key="index">
    {{ item.name }}
  </li>
</template>

<!-- GOOD: When index is acceptable (static lists, no reordering) -->
<template>
  <li v-for="(item, index) in staticItems" :key="`static-${index}`">
    {{ item }}
  </li>
</template>
```

### 条件渲染

```vue
<!-- GOOD: Consistent v-if / v-else-if / v-else chain -->
<template>
  <div v-if="status === 'loading'">
    <LoadingSpinner />
  </div>
  <div v-else-if="status === 'error'">
    <ErrorMessage :message="error" />
  </div>
  <div v-else>
    <Content :data="data" />
  </div>
</template>

<!-- For toggling visibility, use v-show -->
<template>
  <div v-show="isVisible">
    This element stays in DOM
  </div>
</template>
```

---

## 脚本规范

### 变量声明

```typescript
// GOOD: Use const by default, let when reassignment needed
const API_URL = 'https://api.example.com';
const MAX_RETRY = 3;
let retryCount = 0;

// BAD: Never use var
var name = 'test'; // ❌

// GOOD: Use meaningful names
const isLoading = ref(false);
const hasError = ref(false);
const canSubmit = computed(() => !isLoading.value && isValid.value);

// BAD: Unclear names
const flag = ref(false);
const temp = ref(null);
```

### 组合式函数规范

```typescript
// composables/useUser.ts
import { ref, computed, readonly } from 'vue';
import type { User } from '@/types';

// Export as factory function with 'use' prefix
export function useUser() {
  // Private state
  const _user = ref<User | null>(null);
  const _isLoading = ref(false);
  const _error = ref<Error | null>(null);

  // Public computed
  const isLoggedIn = computed(() => _user.value !== null);
  const userName = computed(() => _user.value?.name ?? '');

  // Methods
  const fetchUser = async (id: string) => {
    _isLoading.value = true;
    _error.value = null;
    try {
      const response = await fetch(`/api/users/${id}`);
      _user.value = await response.json();
    } catch (e) {
      _error.value = e as Error;
    } finally {
      _isLoading.value = false;
    }
  };

  const logout = () => {
    _user.value = null;
  };

  // Return reactive state and methods
  return {
    // Readonly state
    user: readonly(_user),
    isLoading: readonly(_isLoading),
    error: readonly(_error),
    // Computed
    isLoggedIn,
    userName,
    // Methods
    fetchUser,
    logout,
  };
}
```

### 错误处理

```typescript
// GOOD: Comprehensive error handling
const fetchData = async () => {
  isLoading.value = true;
  error.value = null;
  
  try {
    const response = await api.getData();
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    data.value = await response.json();
  } catch (e) {
    error.value = e as Error;
    // Log to monitoring service
    logger.error('Failed to fetch data', { error: e });
    // Show user-friendly message
    toast.error('Failed to load data. Please try again.');
  } finally {
    isLoading.value = false;
  }
};

// BAD: Silent error handling
const fetchData = async () => {
  try {
    const data = await api.getData();
    state.value = data;
  } catch (e) {
    // Do nothing - user won't know something went wrong
  }
};
```

---

## 样式规范

### Scoped 样式

```vue
<template>
  <div class="user-card">
    <h2 class="user-card__title">{{ title }}</h2>
    <p class="user-card__description">{{ description }}</p>
  </div>
</template>

<style scoped lang="scss">
// Use BEM naming convention
.user-card {
  padding: 16px;
  border-radius: 8px;
  background: var(--color-bg);

  &__title {
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 8px;
  }

  &__description {
    color: var(--color-text-secondary);
    line-height: 1.5;
  }
}
</style>
```

### CSS 变量使用

```scss
// assets/styles/variables.scss
:root {
  // Colors
  --color-primary: #1890ff;
  --color-success: #52c41a;
  --color-warning: #faad14;
  --color-error: #ff4d4f;
  
  --color-bg: #ffffff;
  --color-bg-secondary: #f5f5f5;
  --color-text: #333333;
  --color-text-secondary: #666666;
  
  // Spacing
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;
  
  // Typography
  --font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-size-sm: 12px;
  --font-size-base: 14px;
  --font-size-lg: 16px;
}

// Dark mode support
@media (prefers-color-scheme: dark) {
  :root {
    --color-bg: #1f1f1f;
    --color-text: #ffffff;
  }
}
```

### 样式穿透

```vue
<style scoped lang="scss">
// GOOD: Use :deep() for style penetration
.parent {
  :deep(.child-component) {
    color: red;
  }
}

// BAD: Avoid :v-deep (deprecated) and >>>
.parent ::v-deep .child-component {  // Deprecated
  color: red;
}
</style>
```

---

## 状态管理

### Pinia Store 规范

```typescript
// stores/modules/user.ts
import { defineStore } from 'pinia';
import type { User } from '@/types';

interface UserState {
  currentUser: User | null;
  token: string | null;
  permissions: string[];
}

export const useUserStore = defineStore('user', {
  state: (): UserState => ({
    currentUser: null,
    token: null,
    permissions: [],
  }),

  getters: {
    isLoggedIn: (state) => !!state.token,
    userName: (state) => state.currentUser?.name ?? 'Guest',
    hasPermission: (state) => {
      return (permission: string) => state.permissions.includes(permission);
    },
  },

  actions: {
    async login(credentials: LoginCredentials) {
      try {
        const response = await authApi.login(credentials);
        this.token = response.token;
        this.currentUser = response.user;
        this.permissions = response.permissions;
      } catch (error) {
        this.$reset();
        throw error;
      }
    },

    logout() {
      this.$reset();
      router.push('/login');
    },

    updateProfile(updates: Partial<User>) {
      if (this.currentUser) {
        this.currentUser = { ...this.currentUser, ...updates };
      }
    },
  },
});
```

### Store 使用规范

```typescript
// GOOD: Destructure in setup
const userStore = useUserStore();
const { currentUser, isLoggedIn } = storeToRefs(userStore);
const { login, logout } = userStore;

// BAD: Destructuring reactive state directly (loses reactivity)
const { currentUser, isLoggedIn } = useUserStore(); // Loses reactivity!

// GOOD: Use storeToRefs for reactive state
import { storeToRefs } from 'pinia';
const { currentUser, isLoggedIn } = storeToRefs(userStore);
```

---

## TypeScript 规范

### 类型定义

```typescript
// types/models/user.ts
export interface User {
  id: string;
  email: string;
  name: string;
  avatar?: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface LoginCredentials {
  email: string;
  password: string;
  rememberMe?: boolean;
}

export type UserRole = 'admin' | 'user' | 'guest';

// Use type for unions, interfaces for objects
export type Status = 'idle' | 'loading' | 'success' | 'error';

export interface ApiResponse<T> {
  data: T;
  message: string;
  code: number;
}
```

### 组件 Props 类型

```typescript
// GOOD: Use type-based declaration
const props = defineProps<{
  id: string;
  title: string;
  items: Item[];
  config?: Config;
}>();

// With defaults
const props = withDefaults(
  defineProps<{
    size?: 'small' | 'medium' | 'large';
    visible?: boolean;
  }>(),
  {
    size: 'medium',
    visible: true,
  }
);
```

### 泛型组件

```typescript
// Generic list component
<script setup lang="ts" generic="T extends { id: string }">
const props = defineProps<{
  items: T[];
  renderItem: (item: T) => VNode;
}>();
</script>
```

---

## 性能优化

### 懒加载组件

```typescript
// router/modules/dashboard.ts
import { lazy } from '@/utils/router';

export default {
  path: '/dashboard',
  component: () => import('@/views/dashboard/Dashboard.vue'), // Lazy load
  children: [
    {
      path: 'analytics',
      component: () => import('@/views/dashboard/Analytics.vue'),
    },
  ],
};

// Or use defineAsyncComponent for conditional loading
import { defineAsyncComponent } from 'vue';

const AsyncModal = defineAsyncComponent(() =>
  import('@/components/Modal.vue')
);
```

### 计算属性优化

```typescript
// GOOD: Use computed for derived state
const filteredItems = computed(() => {
  return items.value.filter(item => item.isActive);
});

// GOOD: Use computed with getter/setter for v-model
const searchQuery = computed({
  get: () => state.query,
  set: debounce((value: string) => {
    state.query = value;
  }, 300),
});

// BAD: Expensive operation without caching
const expensiveValue = computed(() => {
  // This runs on every dependency change
  return heavyCalculation(largeArray.value);
});

// GOOD: Cache expensive operations
const expensiveValue = computed(() => {
  // Only re-computes when largeArray actually changes
  return heavyCalculation(largeArray.value);
});
```

### 列表虚拟化

```vue
<!-- Use virtual scrolling for long lists -->
<script setup lang="ts">
import { useVirtualList } from '@vueuse/core';

const { list, containerProps, wrapperProps } = useVirtualList(
  largeItems,
  { itemHeight: 48 }
);
</script>

<template>
  <div v-bind="containerProps" style="height: 400px; overflow: auto;">
    <div v-bind="wrapperProps">
      <div v-for="{ data, index } in list" :key="data.id" style="height: 48px;">
        {{ index }}: {{ data.name }}
      </div>
    </div>
  </div>
</template>
```

---

## 安全规范

### XSS 防护

```vue
<!-- GOOD: Vue automatically escapes -->
<template>
  <div>{{ userInput }}</div> <!-- Safe -->
</template>

<!-- DANGER: Only use v-html when necessary and sanitize -->
<script setup lang="ts">
import DOMPurify from 'dompurify';

const sanitizedHtml = computed(() => {
  return DOMPurify.sanitize(userHtml.value);
});
</script>

<template>
  <div v-html="sanitizedHtml"></div>
</template>
```

### 敏感数据处理

```typescript
// GOOD: Never log sensitive data
const login = async (credentials: LoginCredentials) => {
  console.log('Attempting login for:', credentials.email); // ✅ Email is usually ok
  // console.log('Password:', credentials.password); // ❌ NEVER log passwords
  
  const response = await authApi.login(credentials);
  return response;
};

// GOOD: Clear sensitive data from memory
const handlePayment = async (cardData: CardData) => {
  const token = await tokenizeCard(cardData);
  cardData.number = ''; // Clear immediately after use
  return processPayment(token);
};
```

### 环境变量

```typescript
// .env.development
VITE_API_BASE_URL=https://dev-api.example.com
VITE_ENABLE_DEBUG=true

// .env.production
VITE_API_BASE_URL=https://api.example.com
VITE_ENABLE_DEBUG=false

// Usage
const apiUrl = import.meta.env.VITE_API_BASE_URL;

// BAD: Hardcoded secrets
const apiKey = 'sk_live_xxxxx'; // ❌ Never do this
```

---

## 代码质量检查清单

提交代码前确认：

- [ ] 组件使用 `<script setup>` 语法
- [ ] 所有 props 都有类型定义
- [ ] 事件命名使用 kebab-case
- [ ] 无复杂逻辑在模板中
- [ ] v-for 都有唯一的 :key
- [ ] 样式使用 scoped
- [ ] 使用 CSS 变量而非硬编码值
- [ ] 长列表使用虚拟滚动
- [ ] 无硬编码密钥或敏感信息
- [ ] 错误处理完善
- [ ] 组件单一职责
- [ ] 无 console.log（使用 logger）
- [ ] 通过 ESLint 和 TypeScript 检查

---

## 推荐工具配置

### ESLint 配置

```javascript
// eslint.config.js
import js from '@eslint/js';
import vue from 'eslint-plugin-vue';
import typescript from '@typescript-eslint/eslint-plugin';
import parser from 'vue-eslint-parser';

export default [
  js.configs.recommended,
  ...vue.configs['flat/recommended'],
  {
    files: ['**/*.vue', '**/*.ts'],
    languageOptions: {
      parser,
      parserOptions: {
        parser: '@typescript-eslint/parser',
      },
    },
    plugins: {
      '@typescript-eslint': typescript,
    },
    rules: {
      'vue/multi-word-component-names': 'error',
      'vue/require-default-prop': 'error',
      'vue/no-v-html': 'warn',
      '@typescript-eslint/no-explicit-any': 'error',
    },
  },
];
```

### VS Code 配置

```json
// .vscode/settings.json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": "explicit"
  },
  "vue.inlayHints.missingProps": true,
  "vue.inlayHints.inlineHandlerLeading": true
}
```

---

## 参考资源

- [Vue 官方风格指南](https://vuejs.org/style-guide/)
- [Vue 官方文档](https://vuejs.org/guide/introduction.html)
- [Pinia 官方文档](https://pinia.vuejs.org/)
- [VueUse 工具库](https://vueuse.org/)
- [ESLint Vue 插件](https://eslint.vuejs.org/)
