import { ElMessage } from 'element-plus'
import { getNextTaskRoute } from './ema'

export function navigateNext(router, delay = 400) {
  setTimeout(() => {
    const next = getNextTaskRoute()
    if (next) router.replace(next)
    else router.replace('/home')
  }, delay)
}

export function goHome(router, delay = 400) {
  setTimeout(() => router.replace('/home'), delay)
}

/**
 * @param {object} options
 * @param {import('vue-router').Router} options.router
 * @param {function} options.submit - returns Promise
 * @param {string} [options.title]
 * @param {string} [options.successToast]
 * @param {boolean} [options.goNext=true]
 * @param {number} [options.delay=400]
 * @param {function} [options.onSuccess]
 * @param {function} [options.onError]
 */
export async function runStepSubmit(options) {
  const {
    router,
    submit,
    successToast,
    goNext = true,
    delay = 400,
    onSuccess,
    onError,
  } = options

  try {
    const result = await submit()
    if (successToast) ElMessage.success(successToast)
    if (onSuccess) {
      await onSuccess(result)
      return result
    }
    if (goNext) navigateNext(router, delay)
    return result
  } catch (err) {
    if (onError) {
      onError(err)
      return
    }
    ElMessage.error(err?.message || '提交失败')
    throw err
  }
}
