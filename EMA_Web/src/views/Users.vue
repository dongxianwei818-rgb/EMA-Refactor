<template>
  <div class="page-users">
    <el-card shadow="never" class="page-card">
      <template #header>
        <div class="card-header">
          <span>用户管理</span>
          <el-button type="primary" :icon="Plus" @click="openCreate">新增用户</el-button>
        </div>
      </template>

      <el-form :inline="true" :model="query" class="filter-form" @submit.prevent>
        <el-form-item label="关键词">
          <el-input
            v-model="query.keyword"
            clearable
            placeholder="用户名"
            style="width: 180px"
            @keyup.enter="onSearch"
          />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="query.role" clearable placeholder="全部" style="width: 120px">
            <el-option label="管理员" :value="0" />
            <el-option label="普通用户" :value="1" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.study_status" clearable placeholder="全部" style="width: 140px">
            <el-option label="active" value="active" />
            <el-option label="consent_revoked" value="consent_revoked" />
            <el-option label="exited" value="exited" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="onSearch">查询</el-button>
          <el-button @click="onReset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table v-loading="loading" :data="items" stripe border style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="user_name" label="用户名" min-width="120" />
        <el-table-column label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="row.role === 0 ? 'danger' : 'info'" size="small">
              {{ row.role === 0 ? '管理员' : '普通用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="study_status" label="状态" width="130" />
        <el-table-column prop="login_count" label="登录次数" width="100" />
        <el-table-column prop="created_at" label="创建时间" min-width="160" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination
          v-model:current-page="query.page"
          v-model:page-size="query.page_size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          background
          @size-change="loadList"
          @current-change="loadList"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑用户' : '新增用户'"
      width="480px"
      destroy-on-close
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="96px">
        <el-form-item label="用户名" prop="user_name">
          <el-input v-model="form.user_name" maxlength="64" />
        </el-form-item>
        <el-form-item :label="isEdit ? '新密码' : '密码'" :prop="isEdit ? undefined : 'psw'">
          <el-input
            v-model="form.psw"
            type="password"
            show-password
            :placeholder="isEdit ? '不修改请留空' : '请输入密码'"
          />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-radio-group v-model="form.role">
            <el-radio :value="1">普通用户</el-radio>
            <el-radio :value="0">管理员</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="状态" prop="study_status">
          <el-select v-model="form.study_status" style="width: 100%">
            <el-option label="active" value="active" />
            <el-option label="consent_revoked" value="consent_revoked" />
            <el-option label="exited" value="exited" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { createUser, deleteUser, fetchUsers, updateUser } from '../api/adminUsers'

const loading = ref(false)
const saving = ref(false)
const items = ref([])
const total = ref(0)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const formRef = ref(null)

const query = reactive({
  keyword: '',
  role: undefined,
  study_status: undefined,
  page: 1,
  page_size: 20,
})

const form = reactive({
  user_name: '',
  psw: '',
  role: 1,
  study_status: 'active',
})

const rules = {
  user_name: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  psw: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  study_status: [{ required: true, message: '请选择状态', trigger: 'change' }],
}

async function loadList() {
  loading.value = true
  try {
    const data = await fetchUsers({
      keyword: query.keyword || undefined,
      role: query.role,
      study_status: query.study_status || undefined,
      page: query.page,
      page_size: query.page_size,
    })
    items.value = data?.items || []
    total.value = data?.total || 0
  } catch (e) {
    ElMessage.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function onSearch() {
  query.page = 1
  loadList()
}

function onReset() {
  query.keyword = ''
  query.role = undefined
  query.study_status = undefined
  query.page = 1
  loadList()
}

function resetForm() {
  form.user_name = ''
  form.psw = ''
  form.role = 1
  form.study_status = 'active'
  editingId.value = null
  isEdit.value = false
}

function openCreate() {
  resetForm()
  isEdit.value = false
  dialogVisible.value = true
}

function openEdit(row) {
  isEdit.value = true
  editingId.value = row.id
  form.user_name = row.user_name
  form.psw = ''
  form.role = row.role === 0 ? 0 : 1
  form.study_status = row.study_status || 'active'
  dialogVisible.value = true
}

async function onSave() {
  if (!isEdit.value) {
    const valid = await formRef.value?.validate().catch(() => false)
    if (!valid) return
  } else if (!form.user_name?.trim()) {
    ElMessage.warning('用户名不能为空')
    return
  }

  saving.value = true
  try {
    if (isEdit.value) {
      const payload = {
        user_name: form.user_name.trim(),
        role: form.role,
        study_status: form.study_status,
      }
      if (form.psw) payload.psw = form.psw
      await updateUser(editingId.value, payload)
      ElMessage.success('用户已更新')
    } else {
      await createUser({
        user_name: form.user_name.trim(),
        psw: form.psw,
        role: form.role,
        study_status: form.study_status,
      })
      ElMessage.success('用户已创建')
    }
    dialogVisible.value = false
    await loadList()
  } catch (e) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function onDelete(row) {
  try {
    await ElMessageBox.confirm(`确认删除用户「${row.user_name}」？此操作不可恢复。`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await deleteUser(row.id)
    ElMessage.success('用户已删除')
    await loadList()
  } catch (e) {
    if (e === 'cancel' || e === 'close') return
    ElMessage.error(e.message || '删除失败')
  }
}

onMounted(loadList)
</script>

<style scoped>
.page-card {
  border-radius: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}

.filter-form {
  margin-bottom: 8px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
