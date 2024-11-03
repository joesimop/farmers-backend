#Defines the CTEs used in the SQL queries
#NOTE: CTEs are not prepended with WITH keyword. It is assumed that the caller will do so.

market_tokens_cte = \
    """
    market_tokens_cte AS (
        SELECT
            id, token_type as type, per_dollar_value
        FROM market_tokens
        WHERE market_id = :market_id
    )
    """

market_vendors_cte = \
    """
    market_vendors_cte AS (
        SELECT
            vendors.id, mv.id as market_vendor_id, business_name, current_cpc, cpc_expr, vendors.type
        FROM vendors
        JOIN market_vendors AS mv ON vendors.id = mv.vendor_id
        WHERE mv.market_id = :market_id
    )
    """
    

market_fees_cte = \
    """
    market_fees_cte AS (
        SELECT vendor_type, fee_type,
        CASE
            WHEN fee_type = 'FLAT_FEE' THEN rate
            WHEN fee_type = 'PERCENT_GROSS' THEN COALESCE(rate_2, 0)
            WHEN fee_type = 'FLAT_PERCENT_COMBO' THEN rate
            WHEN fee_type = 'MAX_OF_EITHER' THEN rate
            WHEN fee_type = 'GOV_FEE' THEN rate
            ELSE 0
        END AS flat,
        CASE
            WHEN fee_type = 'FLAT_FEE' THEN COALESCE(rate_2, 0)
            WHEN fee_type = 'PERCENT_GROSS' THEN rate
            WHEN fee_type = 'FLAT_PERCENT_COMBO' THEN COALESCE(rate_2, 0)
            WHEN fee_type = 'MAX_OF_EITHER' THEN COALESCE(rate_2, 0)
            WHEN fee_type = 'GOV_FEE' THEN 0
            ELSE 0
        END AS percent
        FROM market_fees
        WHERE market_id = :market_id
    )
    """