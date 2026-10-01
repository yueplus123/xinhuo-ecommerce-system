import api from '@/api/xinhuo/client';

const prefix = "/admin/catalog";

export function fetchAdminPlatforms(params) {
  return api.get(`${prefix}/platforms/`, { params });
}

export function createAdminPlatform(payload) {
  return api.post(`${prefix}/platforms/`, payload);
}

export function fetchAdminPlatform(platformId) {
  return api.get(`${prefix}/platforms/${platformId}/`);
}

export function updateAdminPlatform(platformId, payload) {
  return api.patch(`${prefix}/platforms/${platformId}/`, payload);
}

export function deleteAdminPlatform(platformId) {
  return api.delete(`${prefix}/platforms/${platformId}/`);
}

export function reorderAdminPlatforms(order) {
  return api.post(`${prefix}/platforms/reorder/`, { order });
}

export function createAdminBusiness(payload) {
  return api.post(`${prefix}/businesses/`, payload);
}

export function updateAdminBusiness(businessId, payload) {
  return api.patch(`${prefix}/businesses/${businessId}/`, payload);
}

export function deleteAdminBusiness(businessId) {
  return api.delete(`${prefix}/businesses/${businessId}/`);
}

export function createAdminSku(payload) {
  return api.post(`${prefix}/skus/`, payload);
}

export function updateAdminSku(skuId, payload) {
  return api.patch(`${prefix}/skus/${skuId}/`, payload);
}

export function deleteAdminSku(skuId) {
  return api.delete(`${prefix}/skus/${skuId}/`);
}

export function duplicateAdminSku(skuId) {
  return api.post(`${prefix}/skus/${skuId}/duplicate/`);
}

export function fetchPlatformTagPool() {
  return api.get("/platform-tag-pool/");
}
