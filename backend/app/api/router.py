from fastapi import APIRouter

from app.api.accounts import router as accounts_router
from app.api.holdings import router as holdings_router
from app.api.transactions import router as transactions_router
from app.api.liabilities import router as liabilities_router
from app.api.market import router as market_router
from app.api.dashboard import router as dashboard_router
from app.api.snapshots import router as snapshots_router
from app.api.expenses import router as expenses_router
from app.api.repayment import router as repayment_router
from app.api.bill_import import router as bill_import_router
from app.api.backup import router as backup_router

api_router = APIRouter()

api_router.include_router(accounts_router, prefix="/accounts", tags=["accounts"])
api_router.include_router(holdings_router, prefix="/holdings", tags=["holdings"])
api_router.include_router(transactions_router, prefix="/transactions", tags=["transactions"])
api_router.include_router(liabilities_router, prefix="/liabilities", tags=["liabilities"])
api_router.include_router(market_router, prefix="/market", tags=["market"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(snapshots_router, prefix="/snapshots", tags=["snapshots"])
api_router.include_router(expenses_router, prefix="/expenses", tags=["expenses"])
api_router.include_router(repayment_router, prefix="/repayment-plans", tags=["repayment"])
api_router.include_router(bill_import_router, prefix="/import", tags=["import"])
api_router.include_router(backup_router, prefix="/backup", tags=["backup"])
