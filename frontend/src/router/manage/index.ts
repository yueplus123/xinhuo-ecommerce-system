import { manageRoutes as catalog } from './catalog'
import { manageRoutes as pools } from './pools'
import { manageRoutes as content } from './content'
import { manageRoutes as accounts } from './accounts'

export const manageRoutes: AppRouteRecordRaw[] = [...catalog, ...pools, ...content, ...accounts]
