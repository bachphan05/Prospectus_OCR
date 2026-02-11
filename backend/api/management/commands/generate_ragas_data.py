import json
import pandas as pd
from django.core.management.base import BaseCommand
from api.models import Document
from api.services import RAGService

class Command(BaseCommand):
    help = 'Generates evaluation dataset for RAGAS'

    def add_arguments(self, parser):
        parser.add_argument('document_id', type=int, help='ID of the document to test')

    def handle(self, *args, **options):
        doc_id = options['document_id']
        rag_service = RAGService()

        # 1. Define your Test Questions (Ground Truth is optional but recommended)
        test_cases = [
    # --- NHÓM 1: THÔNG TIN PHÁP LÝ & THỰC THỂ (1-10) ---
    {
        "question": "Tên đầy đủ và tên viết tắt của quỹ là gì?",
        "ground_truth": "Tên đầy đủ: Quỹ Đầu tư Trái phiếu Gia tăng Thu nhập Cố định DC. Tên viết tắt: DCIP."
    },
    {
        "question": "Công ty quản lý quỹ là công ty nào?",
        "ground_truth": "Công ty Cổ phần Quản lý Quỹ Đầu tư Việt Nam (DCVFM)."
    },
    {
        "question": "Ngân hàng giám sát của quỹ DCIP là ngân hàng nào?",
        "ground_truth": "Ngân hàng TNHH Một thành viên Standard Chartered (Việt Nam)."
    },
    {
        "question": "Giấy chứng nhận đăng ký lập quỹ đại chúng số bao nhiêu và do ai cấp?",
        "ground_truth": "Số 36/GCN-UBCK do Ủy ban Chứng khoán Nhà nước (UBCKNN) cấp ngày 03 tháng 4 năm 2019."
    },
    {
        "question": "Bản cáo bạch này có hiệu lực chính thức từ thời điểm nào?",
        "ground_truth": "Có hiệu lực kể từ 11h30 ngày 21 tháng 01 năm 2025."
    },
    {
        "question": "Loại hình quỹ của DCIP là gì?",
        "ground_truth": "Quỹ đại chúng dạng mở."
    },
    {
        "question": "Định kỳ bao lâu thì Bản cáo bạch được cập nhật?",
        "ground_truth": "Cập nhật khi phát sinh thông tin quan trọng hoặc định kỳ ít nhất 06 tháng một lần."
    },
    {
        "question": "Đơn vị nào thực hiện kiểm toán cho quỹ DCIP?",
        "ground_truth": "Công ty Kiểm toán được Đại hội Nhà đầu tư hoặc Ban đại diện Quỹ lựa chọn từ danh sách đề xuất."
    },
    {
        "question": "Đại hội Nhà đầu tư thường niên được tổ chức khi nào?",
        "ground_truth": "Mỗi năm một lần, trong thời hạn 04 tháng kể từ ngày kết thúc năm tài chính."
    },
    {
        "question": "Năm tài chính của quỹ được quy định như thế nào?",
        "ground_truth": "Bắt đầu từ ngày 01 tháng 01 đến hết ngày 31 tháng 12 dương lịch hàng năm."
    },

    # --- NHÓM 2: CHIẾN LƯỢC ĐẦU TƯ & RỦI RO (11-20) ---
    {
        "question": "Mục tiêu đầu tư của quỹ DCIP là gì?",
        "ground_truth": "Tối ưu hóa lợi nhuận thông qua đầu tư vào tài sản có thu nhập cố định, công cụ thị trường tiền tệ và trái phiếu chất lượng tín dụng tốt."
    },
    {
        "question": "Quỹ DCIP đầu tư vào những loại trái phiếu nào?",
        "ground_truth": "Trái phiếu Chính phủ, trái phiếu chính quyền địa phương, trái phiếu được Chính phủ bảo lãnh và trái phiếu doanh nghiệp."
    },
    {
        "question": "Tiêu chí lựa chọn trái phiếu doanh nghiệp của quỹ là gì?",
        "ground_truth": "Trái phiếu có chất lượng tín dụng tốt, đảm bảo khả năng thanh toán gốc và lãi đúng hạn."
    },
    {
        "question": "Quỹ có được phép đầu tư vào cổ phiếu không?",
        "ground_truth": "Tài liệu tập trung vào tài sản thu nhập cố định và trái phiếu; việc đầu tư cổ phiếu phải tuân thủ hạn mức trong Điều lệ (thường là tỷ lệ rất thấp hoặc không có trong quỹ trái phiếu thuần)."
    },
    {
        "question": "Rủi ro thanh khoản được mô tả như thế nào trong tài liệu?",
        "ground_truth": "Là rủi ro Quỹ khó bán tài sản nhanh chóng để đáp ứng nhu cầu rút vốn của nhà đầu tư mà không làm giảm đáng kể giá trị tài sản."
    },
    {
        "question": "Hạn mức vay nợ của Quỹ được quy định ra sao?",
        "ground_truth": "Quỹ chỉ được vay ngắn hạn để trang trải các chi phí cần thiết hoặc thanh toán lệnh mua lại, hạn mức không quá 5% giá trị tài sản ròng."
    },
    {
        "question": "Thời hạn vay tối đa của Quỹ là bao nhiêu ngày?",
        "ground_truth": "Tối đa là 30 ngày."
    },
    {
        "question": "Ai là người chịu trách nhiệm thẩm định giá trị tài sản ròng (NAV) của quỹ?",
        "ground_truth": "Ngân hàng giám sát phối hợp cùng Công ty Quản lý quỹ."
    },
    {
        "question": "Trường hợp nào quỹ sẽ tạm dừng giao dịch chứng chỉ quỹ?",
        "ground_truth": "Khi xảy ra sự kiện bất khả kháng, không định giá được NAV hoặc theo yêu cầu của UBCKNN."
    },
    {
        "question": "Quỹ có cam kết lợi nhuận cố định cho nhà đầu tư không?",
        "ground_truth": "Không. Đầu tư vào chứng chỉ quỹ luôn có rủi ro và kết quả trong quá khứ không đảm bảo cho tương lai."
    },

    # --- NHÓM 3: GIAO DỊCH, PHÍ & VẬN HÀNH (21-30) ---
    {
        "question": "Tần suất giao dịch của quỹ DCIP là bao lâu một lần?",
        "ground_truth": "Giao dịch hàng ngày, từ thứ Hai đến thứ Sáu hàng tuần."
    },
    {
        "question": "Lệnh giao dịch của nhà đầu tư được gửi đến đâu?",
        "ground_truth": "Gửi đến Công ty Quản lý quỹ hoặc các Đại lý phân phối được chỉ định."
    },
    {
        "question": "Giá mua hoặc giá bán chứng chỉ quỹ được xác định tại thời điểm nào?",
        "ground_truth": "Dựa trên giá trị tài sản ròng (NAV) trên một đơn vị quỹ tại Ngày giao dịch."
    },
    {
        "question": "Mức sai số cho phép khi định giá NAV là bao nhiêu?",
        "ground_truth": "Phải đảm bảo theo quy định pháp luật hiện hành (thường là 0,75% đối với quỹ trái phiếu)."
    },
    {
        "question": "Hàng năm Công ty Quản lý quỹ phải đề xuất bao nhiêu công ty kiểm toán?",
        "ground_truth": "Ít nhất hai (02) Công ty Kiểm toán."
    },
    {
        "question": "Ngân hàng giám sát có trách nhiệm gì đối với tài sản của Quỹ?",
        "ground_truth": "Bảo quản, lưu ký tài sản, giám sát hoạt động quản lý tài sản của Công ty Quản lý quỹ nhằm bảo vệ quyền lợi Nhà đầu tư."
    },
    {
        "question": "Trường hợp nào Ngân hàng giám sát bị thay thế?",
        "ground_truth": "Khi vi phạm nghĩa vụ nghiêm trọng, bị giải thể, phá sản hoặc theo quyết định của Đại hội Nhà đầu tư."
    },
    {
        "question": "Nhà đầu tư có thể xem báo cáo tài chính của quỹ ở đâu?",
        "ground_truth": "Trên trang thông tin điện tử (website) của Công ty Quản lý quỹ DCVFM."
    },
    {
        "question": "Phí quản lý quỹ được tính trên cơ sở nào?",
        "ground_truth": "Tính theo tỷ lệ phần trăm (%) trên giá trị tài sản ròng (NAV) của Quỹ."
    },
    {
        "question": "Việc phân phối lợi nhuận của quỹ được thực hiện khi nào?",
        "ground_truth": "Thực hiện theo quyết định của Đại hội Nhà đầu tư, phù hợp với kết quả kinh doanh và quy định pháp luật."
    }
]

        results = {
            "question": [],
            "answer": [],
            "contexts": [],
            "ground_truth": []
        }

        print(f"--- Generating RAGAS Data for Doc ID {doc_id} ---")

        for case in test_cases:
            q = case["question"]
            print(f"Processing: {q}")

            # Call the service with return_sources=True
            response_data = rag_service.chat(doc_id, q, return_sources=True)

            # Append to lists
            results["question"].append(q)
            results["answer"].append(response_data["text"])
            results["contexts"].append(response_data["contexts"]) # List of strings
            results["ground_truth"].append(case["ground_truth"])

        # Convert to Pandas DataFrame
        df = pd.DataFrame(results)
        
        # Save to CSV
        output_file = "ragas_dataset.csv"
        df.to_csv(output_file, index=False)
        
        print(f"✅ Success! Dataset saved to {output_file}")
        print("You can now load this CSV in your evaluation.py script.")