from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_categories():
    return [
        {
            "code": "oil",
            "name_ko": "기름값",
            "name_en": "Oil",
            "group_code": "energy",
            "keywords": ["oil", "crude", "petroleum", "opec", "barrel"],
            "sort_order": 1
        },
        {
            "code": "fuel",
            "name_ko": "주유비",
            "name_en": "Fuel",
            "group_code": "energy",
            "keywords": ["fuel", "gasoline", "petrol", "diesel"],
            "sort_order": 2
        },
        {
            "code": "gas",
            "name_ko": "가스비",
            "name_en": "Gas",
            "group_code": "energy",
            "keywords": ["gas", "natural gas", "lng", "lpg"],
            "sort_order": 3
        },
        {
            "code": "energy",
            "name_ko": "전기세",
            "name_en": "Energy",
            "group_code": "energy",
            "keywords": ["energy", "electricity", "power", "utility"],
            "sort_order": 4
        },
        {
            "code": "food",
            "name_ko": "장바구니",
            "name_en": "Food",
            "group_code": "living",
            "keywords": ["food", "grocery", "meat", "dairy", "produce"],
            "sort_order": 5
        },
        {
            "code": "wheat",
            "name_ko": "쌀·밀가루",
            "name_en": "Wheat",
            "group_code": "living",
            "keywords": ["wheat", "grain", "corn", "rice", "soybean"],
            "sort_order": 6
        },
        {
            "code": "commodity",
            "name_ko": "생활용품",
            "name_en": "Commodity",
            "group_code": "living",
            "keywords": ["commodity", "raw material", "iron", "steel", "cotton"],
            "sort_order": 7
        },
        {
            "code": "price",
            "name_ko": "물가",
            "name_en": "Price",
            "group_code": "economy",
            "keywords": ["price", "consumer price", "cpi"],
            "sort_order": 8
        },
        {
            "code": "cost",
            "name_ko": "생활비",
            "name_en": "Cost",
            "group_code": "economy",
            "keywords": ["cost", "living cost", "expense", "wage"],
            "sort_order": 9
        },
        {
            "code": "inflation",
            "name_ko": "물가상승",
            "name_en": "Inflation",
            "group_code": "economy",
            "keywords": ["inflation", "deflation", "stagflation"],
            "sort_order": 10
        },
        {
            "code": "shipping",
            "name_ko": "택배·운송비",
            "name_en": "Shipping",
            "group_code": "supply_chain",
            "keywords": ["shipping", "freight", "logistics", "supply chain", "port"],
            "sort_order": 11
        }
    ]
