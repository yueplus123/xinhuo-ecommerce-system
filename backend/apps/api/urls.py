from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import admin_catalog_views, ledger_views, manage_accounts, manage_catalog, manage_content, manage_pools, views

app_name = "api"

router = DefaultRouter()
router.register("hall-blocks", views.HallBlockViewSet, basename="hall-block")
router.register(
    "subscription-platform-options",
    views.SubscriptionPlatformOptionViewSet,
    basename="subscription-platform-option",
)
router.register("subscription-reminders", views.SubscriptionReminderViewSet, basename="subscription-reminder")
router.register("material-renewals", views.MaterialRenewalViewSet, basename="material-renewal")
router.register("common-cards", views.CommonCardViewSet, basename="common-card")
router.register("common-accounts", views.CommonAccountViewSet, basename="common-account")

urlpatterns = [
    path("auth/token/", views.ApiTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", views.ApiTokenRefreshView.as_view(), name="token_refresh"),
    path("auth/me/", views.MeAPIView.as_view(), name="me"),
    path("auth/me/avatar/", views.MeAvatarAPIView.as_view(), name="me-avatar"),
    path("auth/me/login-logs/", views.MeLoginLogsAPIView.as_view(), name="me-login-logs"),
    path("staff-users/", views.StaffUsersListAPIView.as_view(), name="staff-users"),
    path("ledger/health/", ledger_views.LedgerHealthAPIView.as_view(), name="ledger-health"),
    path("ledger/catalog/", ledger_views.LedgerCatalogAPIView.as_view(), name="ledger-catalog"),
    path(
        "ledger/catalog/businesses/<str:pk>/",
        ledger_views.LedgerCatalogBusinessDetailAPIView.as_view(),
        name="ledger-catalog-business",
    ),
    path(
        "ledger/catalog/businesses/<str:bid>/options/",
        ledger_views.LedgerCatalogOptionAPIView.as_view(),
        name="ledger-catalog-option-create",
    ),
    path(
        "ledger/catalog/businesses/<str:bid>/options/<str:oid>/",
        ledger_views.LedgerCatalogOptionAPIView.as_view(),
        name="ledger-catalog-option",
    ),
    path("ledger/ledger/batch-import/", ledger_views.LedgerBatchImportAPIView.as_view(), name="ledger-batch-import"),
    path("ledger/ledger/bulk-status/", ledger_views.LedgerBulkStatusAPIView.as_view(), name="ledger-bulk-status"),
    path("ledger/meta/", ledger_views.LedgerMetaAPIView.as_view(), name="ledger-meta"),
    path("ledger/ledger/", ledger_views.LedgerListAPIView.as_view(), name="ledger-list"),
    path("ledger/ledger/<str:pk>/", ledger_views.LedgerDetailAPIView.as_view(), name="ledger-detail"),
    path("ledger/ledger/<str:pk>/settle/", ledger_views.LedgerSettleAPIView.as_view(), name="ledger-settle"),
    path("ledger/ledger/<str:pk>/status/", ledger_views.LedgerStatusAPIView.as_view(), name="ledger-status"),
    path("ledger/wallet/", ledger_views.WalletListAPIView.as_view(), name="ledger-wallet-list"),
    path("ledger/wallet/<str:pk>/", ledger_views.WalletDetailAPIView.as_view(), name="ledger-wallet-detail"),
    path("ledger/stats/", ledger_views.LedgerStatsAPIView.as_view(), name="ledger-stats"),
    path("data-screen/", views.DataScreenAPIView.as_view(), name="data-screen"),
    path("platforms/", views.PlatformListAPIView.as_view(), name="platform_list"),
    path(
        "platforms/export-businesses/",
        views.PlatformBusinessExportAPIView.as_view(),
        name="platform-export-businesses",
    ),
    path("platforms/<int:pk>/", views.PlatformDetailAPIView.as_view(), name="platform_detail"),
    path("admin/catalog/platforms/", admin_catalog_views.AdminPlatformListCreateAPIView.as_view(), name="admin-catalog-platforms"),
    path("admin/catalog/platforms/reorder/", admin_catalog_views.AdminPlatformReorderAPIView.as_view(), name="admin-catalog-platforms-reorder"),
    path("admin/catalog/platforms/<int:pk>/", admin_catalog_views.AdminPlatformWorkbenchAPIView.as_view(), name="admin-catalog-platform"),
    path("admin/catalog/businesses/", admin_catalog_views.AdminBusinessCreateAPIView.as_view(), name="admin-catalog-businesses"),
    path("admin/catalog/businesses/<int:pk>/", admin_catalog_views.AdminBusinessDetailAPIView.as_view(), name="admin-catalog-business"),
    path("admin/catalog/skus/", admin_catalog_views.AdminSkuCreateAPIView.as_view(), name="admin-catalog-skus"),
    path("admin/catalog/skus/<int:pk>/", admin_catalog_views.AdminSkuDetailAPIView.as_view(), name="admin-catalog-sku"),
    path("admin/catalog/skus/<int:pk>/duplicate/", admin_catalog_views.AdminSkuDuplicateAPIView.as_view(), name="admin-catalog-sku-duplicate"),
    path("payment-records/batch-submit/", views.PaymentBatchSubmitAPIView.as_view(), name="payment-records-batch-submit"),
    path("payment-records/export/", views.PaymentRecordExportAPIView.as_view(), name="payment-records-export"),
    path("payment-records/", views.PaymentRecordListCreateAPIView.as_view(), name="payment-records"),
    path("payment-meta/", views.PaymentMetaAPIView.as_view(), name="payment-meta"),
    path(
        "external/payments/push/",
        views.ExternalPaymentPushAPIView.as_view(),
        name="external-payment-push",
    ),
    path(
        "external/wechat-bot/push/",
        views.ExternalWechatBotPushAPIView.as_view(),
        name="external-wechat-bot-push",
    ),
    path(
        "external/wechat-bot/products/",
        views.ExternalBotProductQueryAPIView.as_view(),
        name="external-wechat-bot-products",
    ),
    path(
        "external/bridge/health/",
        views.ExternalBridgeHealthAPIView.as_view(),
        name="external-bridge-health",
    ),
    path(
        "external/ledger/push/",
        views.ExternalLedgerPushAPIView.as_view(),
        name="external-ledger-push",
    ),
    path(
        "wechat-bot/records/",
        views.WechatBotRecordListAPIView.as_view(),
        name="wechat-bot-records",
    ),
    path(
        "wechat-bot/records/batch-delete/",
        views.WechatBotRecordBatchDeleteAPIView.as_view(),
        name="wechat-bot-records-batch-delete",
    ),
    path(
        "wechat-bot/records/<int:pk>/",
        views.WechatBotRecordDetailAPIView.as_view(),
        name="wechat-bot-record-detail",
    ),
    path(
        "wechat-bot/employees/",
        views.WechatBotEmployeeListAPIView.as_view(),
        name="wechat-bot-employees",
    ),
    path("payment-tutorials/", views.PaymentTutorialListAPIView.as_view(), name="payment-tutorials"),
    path("tutorial-pool/", views.TutorialPoolListAPIView.as_view(), name="tutorial-pool"),
    path("phrase-pool/", views.PhrasePoolListAPIView.as_view(), name="phrase-pool"),
    path("platform-tag-pool/", views.PlatformTagPoolListAPIView.as_view(), name="platform-tag-pool"),
    path("channel-tag-pool/", views.ChannelTagPoolListAPIView.as_view(), name="channel-tag-pool"),
    path("usd-proxy-price-tiers/", views.UsdProxyPriceTierListAPIView.as_view(), name="usd-proxy-price-tiers"),
    path("nanny-tutorials/", views.NannyTutorialListAPIView.as_view(), name="nanny-tutorials"),
    path("platform-accounts/", views.PlatformAccountListAPIView.as_view(), name="platform-accounts"),
    path("shared-apple-id-pages/", views.SharedAppleIDPageListAPIView.as_view(), name="shared-apple-id-pages"),
    path("pict-cart-pages/", views.PictCartPageListAPIView.as_view(), name="pict-cart-pages"),
    path("fanbox-stats-pages/", views.FanboxStatsPageListAPIView.as_view(), name="fanbox-stats-pages"),
    path("service-monitor-pages/", views.ServiceMonitorPageListAPIView.as_view(), name="service-monitor-pages"),
    path("", include(router.urls)),
    *manage_catalog.urlpatterns,
    *manage_pools.urlpatterns,
    *manage_content.urlpatterns,
    *manage_accounts.urlpatterns,
]
