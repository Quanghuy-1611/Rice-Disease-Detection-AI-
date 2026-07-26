import React, { useState } from 'react';

// Sắp xếp các bệnh theo mức độ phổ biến dễ gặp nhất trên lúa
export const DISEASES = [
  {
    id: "blast",
    name: "Bệnh Đạo Ôn",
    nameEn: "Blast (Pyricularia oryzae)",
    emoji: "🦠",
    severity: "high",
    symptoms: "Bệnh rất phổ biến. Vết bệnh trên lá ban đầu là những chấm nhỏ màu xanh lục sẫm, sau chuyển thành hình thoi (mắt én), tâm màu xám tro, viền nâu đậm. Bệnh nặng các vết nối liền nhau làm cháy toàn bộ lá (đạo ôn lá) hoặc gãy gục cổ bông (đạo ôn cổ bông).",
    cause: "Do nấm Pyricularia oryzae gây ra. Phát triển mạnh trong điều kiện thời tiết âm u, sương mù, độ ẩm cao.",
    treatment: [
      "Sử dụng giống lúa kháng đạo ôn.",
      "Không bón thừa phân đạm (N), bón kali hợp lý.",
      "Khi phát hiện bệnh, ngừng bón đạm, giữ nước ruộng và phun thuốc đặc trị chứa hoạt chất Tricyclazole, Isoprothiolane hoặc Fenoxanil."
    ]
  },
  {
    id: "sheath_blight",
    name: "Bệnh Khô Vằn",
    nameEn: "Sheath Blight",
    emoji: "🌾",
    severity: "high",
    symptoms: "Thường xuất hiện từ giai đoạn đẻ nhánh tối đa. Vết bệnh ban đầu hình bầu dục màu lục tối, sau đó lan rộng thành dạng vằn vện, loang lổ như da hổ. Bệnh làm khô lá chân, nếu lan lên bẹ lá và bông sẽ làm lép hạt.",
    cause: "Nấm Rhizoctonia solani. Lây lan nhanh khi sạ dày, bón nhiều đạm, ruộng ngập nước liên tục.",
    treatment: [
      "Gieo sạ với mật độ thưa hợp lý, không bón thừa đạm.",
      "Vệ sinh đồng ruộng, dọn sạch cỏ dại và tàn dư thực vật.",
      "Phun thuốc chứa Validamycin, Hexaconazole hoặc Azoxystrobin khi bệnh chớm xuất hiện ở bẹ lá."
    ]
  },
  {
    id: "bacterial_leaf_blight",
    name: "Bệnh Bạc Lá (Cháy lá)",
    nameEn: "Bacterial Leaf Blight",
    emoji: "🍂",
    severity: "high",
    symptoms: "Vết bệnh bắt đầu từ mép lá hoặc chóp lá, lan dần vào trong thành các vệt dài màu vàng nhạt hoặc trắng xám. Ranh giới giữa phần bệnh và phần khỏe có hình gợn sóng.",
    cause: "Vi khuẩn Xanthomonas oryzae pv. oryzae. Thường bùng phát sau những trận mưa to, gió lớn.",
    treatment: [
      "Sử dụng giống lúa có gen kháng vi khuẩn bạc lá.",
      "Bón phân cân đối N-P-K, tuyệt đối không phun phân bón lá khi bệnh đang phát triển.",
      "Sử dụng thuốc diệt khuẩn chuyên dụng có hoạt chất Bismerthiazol hoặc Bronopol."
    ]
  },
  {
    id: "bacterial_leaf_streak",
    name: "Bệnh Sọc Lá Vi Khuẩn",
    nameEn: "Bacterial Leaf Streak",
    emoji: "🍂",
    severity: "medium",
    symptoms: "Xuất hiện các vệt nhỏ, hẹp, trong suốt dọc theo gân lá, sau đó chuyển sang màu nâu hoặc vàng nâu. Vết bệnh kéo dài nhưng bị giới hạn bởi các gân lá, tạo thành dạng sọc.",
    cause: "Vi khuẩn Xanthomonas oryzae pv. oryzicola.",
    treatment: [
      "Không bón thừa phân đạm, nhất là vào cuối vụ.",
      "Vệ sinh đồng ruộng, dọn sạch cỏ dại.",
      "Phun thuốc kháng khuẩn như Streptomycin, Kasugamycin khi phát hiện bệnh."
    ]
  },
  {
    id: "bacterial_panicle_blight",
    name: "Bệnh Cháy Gié Vi Khuẩn",
    nameEn: "Bacterial Panicle Blight",
    emoji: "🌾",
    severity: "high",
    symptoms: "Gây cháy, khô hạt và gié lúa. Hạt lúa bị đốm xám đen, sau đó lép và thối, cuống gié lúa cũng bị chuyển màu nâu sẫm.",
    cause: "Vi khuẩn Burkholderia glumae. Phát triển mạnh trong thời tiết nóng và ẩm lúc lúa trổ.",
    treatment: [
      "Xử lý hạt giống trước khi gieo.",
      "Sử dụng giống có khả năng chống chịu.",
      "Phun thuốc diệt khuẩn vào giai đoạn lúa chuẩn bị trổ hoặc trổ đều."
    ]
  },
  {
    id: "downy_mildew",
    name: "Bệnh Sương Mai",
    nameEn: "Downy Mildew",
    emoji: "🌫️",
    severity: "medium",
    symptoms: "Lá có các đốm nhạt màu hoặc hơi vàng, mặt dưới lá có thể xuất hiện lớp mốc trắng mịn vào sáng sớm. Cây lúa có thể bị lùn và trổ bông kém.",
    cause: "Nấm Sclerophthora macrospora. Phát triển mạnh ở ruộng trũng, ứ đọng nước dài ngày.",
    treatment: [
      "Phơi ruộng, quản lý nguồn nước tốt, không để ngập úng kéo dài.",
      "Vệ sinh đồng ruộng, diệt sạch tàn dư thực vật.",
      "Dùng thuốc đặc trị sương mai chứa Metalaxyl hoặc Mancozeb."
    ]
  },
  {
    id: "dead_heart",
    name: "Bệnh Đục Thân (Dead Heart)",
    nameEn: "Dead Heart",
    emoji: "🥀",
    severity: "high",
    symptoms: "Đỉnh sinh trưởng của cây lúa bị héo khô rũ xuống, lá non cuộn tròn lại và chết vàng. Khi nhổ nhẹ dảnh lúa lên sẽ bị đứt ở gốc và ngửi thấy mùi hôi thối.",
    cause: "Đây là triệu chứng điển hình do Sâu Đục Thân phá hoại ở giai đoạn lúa đẻ nhánh non.",
    treatment: [
      "Điều trị tận gốc bằng cách diệt trừ Sâu đục thân.",
      "Sử dụng thuốc lưu dẫn hoặc rải thuốc hạt sát gốc."
    ]
  },

  {
    id: "brown_spot",
    name: "Bệnh Đốm Nâu",
    nameEn: "Brown Spot",
    emoji: "🟤",
    severity: "medium",
    symptoms: "Vết bệnh hình bầu dục tròn, kích thước nhỏ bằng hạt vừng, màu nâu đậm. Thường xuất hiện trên những chân ruộng đất xấu, thiếu dinh dưỡng hoặc ngộ độc hữu cơ.",
    cause: "Nấm Bipolaris oryzae.",
    treatment: [
      "Cải tạo đất, bón lót phân chuồng, phân lân và bổ sung đầy đủ NPK.",
      "Xử lý hạt giống bằng nước ấm 54 độ C trước khi gieo sạ.",
      "Phun thuốc chứa Propiconazole hoặc Difenoconazole nếu tỷ lệ bệnh cao."
    ]
  },
  {
    id: "tungro",
    name: "Bệnh Vàng Lùn, Lùn Xoắn Lá",
    nameEn: "Tungro / Ragged Stunt",
    emoji: "🟡",
    severity: "high",
    symptoms: "Cây lúa thấp lùn, lá chuyển màu vàng cam từ chóp lá lan xuống. Đẻ nhánh kém, bông lúa ngắn, trổ không thoát, hạt lép.",
    cause: "Do virus lây truyền qua trung gian là rầy nâu và rầy xanh đuôi đen.",
    treatment: [
      "Bệnh do virus không có thuốc trị, bắt buộc phải phòng ngừa qua việc quản lý rầy.",
      "Nhổ bỏ và tiêu hủy các cây lúa bị bệnh từ sớm để tránh lây lan.",
      "Cày ải phơi đất, gieo cấy đồng loạt để né rầy."
    ]
  },
  {
    id: "hispa",
    name: "Sâu Gai (Bọ Gai)",
    nameEn: "Hispa",
    emoji: "🐞",
    severity: "low",
    symptoms: "Sâu non ăn mô lá nằm giữa hai lớp biểu bì, để lại lớp biểu bì mỏng màu trắng tạo thành các vết sọc dọc theo gân lá. Trưởng thành gặm bề mặt lá để lại vệt xước.",
    cause: "Côn trùng (Dicladispa armigera).",
    treatment: [
      "Cắt bỏ phần chóp lá khi cấy (nếu có trứng bọ gai).",
      "Bảo vệ thiên địch (ong ký sinh trứng).",
      "Chỉ phun thuốc khi mật độ bọ gai thực sự cao, ảnh hưởng lớn đến quang hợp."
    ]
  },
  {
    id: "leaf_smut",
    name: "Bệnh Than Đen (Leaf Smut)",
    nameEn: "Leaf Smut",
    emoji: "⬛",
    severity: "medium",
    symptoms: "Bệnh thể hiện qua các đốm hoặc vệt nhỏ hơi nổi lên trên bề mặt lá, chứa bào tử nấm màu đen, giống như những vết than. Khi nốt sưng vỡ, bào tử phân tán ra ngoài.",
    cause: "Do nấm Entyloma oryzae gây ra. Phát triển mạnh trong điều kiện môi trường có độ ẩm không khí rất cao và mưa nhiều.",
    treatment: [
      "Sử dụng giống lúa kháng hoặc ít mẫn cảm với bệnh than đen.",
      "Xử lý hạt giống trước khi gieo trồng bằng các loại thuốc diệt nấm phổ rộng.",
      "Đảm bảo khoảng cách gieo cấy hợp lý để tăng độ thông thoáng, giảm độ ẩm tiểu khí hậu trong ruộng.",
      "Phun các loại thuốc trừ nấm có chứa Propiconazole hoặc Tebuconazole khi thấy có triệu chứng bệnh."
    ]
  },
  {
    id: "stem_borer",
    name: "Sâu Đục Thân",
    nameEn: "Rice Stem Borer",
    emoji: "🐛",
    severity: "high",
    symptoms: "Bướm đẻ trứng trên lá, ấu trùng nở ra đục vào thân lúa. Cắt đứt mạch dẫn nhựa khiến dảnh lúa héo úa (hiện tượng dảnh héo - dead heart) ở giai đoạn đẻ nhánh, hoặc làm bông lúa bạc trắng, lép hạt ở giai đoạn trổ.",
    cause: "Các loài bướm hai chấm (Chilo suppressalis), bướm cú mèo... phát sinh mạnh khi gieo sạ dày, bón thừa đạm.",
    treatment: [
      "Ngắt bỏ ổ trứng trên lá ngay từ khi lúa đẻ nhánh.",
      "Sử dụng thiên địch tự nhiên như ong ký sinh trứng (Trichogramma).",
      "Sử dụng thuốc bảo vệ thực vật lưu dẫn khi mật độ bướm/sâu non cao vượt ngưỡng an toàn."
    ]
  },
  {
    id: "leaf_roller",
    name: "Sâu Cuốn Lá Nhỏ",
    nameEn: "Rice Leaf Folder / Rice Skipper",
    emoji: "🐛",
    severity: "medium",
    symptoms: "Sâu non nhả tơ cuốn 2 mép lá lại với nhau tạo thành bao, nằm bên trong gặm ăn chất xanh làm lá bị bạc trắng. Mất diện tích quang hợp nghiêm trọng.",
    cause: "Do bướm Cnaphalocrocis medinalis đẻ trứng. Bùng phát mạnh ở những ruộng xanh tốt, bón nhiều đạm muộn.",
    treatment: [
      "Trồng các loại hoa trên bờ ruộng để thu hút thiên địch (nhện, bọ rùa).",
      "Sử dụng chế phẩm vi sinh (Nấm xanh, Nấm trắng, vi khuẩn Bt).",
      "Hạn chế phun thuốc sâu ở giai đoạn đầu để bảo tồn thiên địch, chỉ phun khi mật độ sâu rất cao lúc lúa làm đòng."
    ]
  },
  {
    id: "brown_planthopper",
    name: "Rầy Nâu",
    nameEn: "Brown Planthopper",
    emoji: "🪲",
    severity: "high",
    symptoms: "Rầy chích hút nhựa ở phần gốc thân lúa làm cây khô héo, chuyển màu nâu, đổ gục (hiện tượng cháy rầy). Ngoài ra còn là môi giới truyền bệnh vàng lùn.",
    cause: "Côn trùng (Nilaparvata lugens). Phất triển mạnh ở những ruộng lúa cấy dày, bón thừa đạm, ngập nước thường xuyên.",
    treatment: [
      "Thực hiện '3 giảm 3 tăng' và '1 phải 5 giảm'.",
      "Bảo vệ thiên địch tự nhiên (nhện bắt mồi, bọ rùa, ong ký sinh).",
      "Khi mật độ rầy cao, rẽ lúa phun thuốc sát gốc bằng các hoạt chất Pymetrozine hoặc Buprofezin."
    ]
  },
  {
    id: "whitebacked_planthopper",
    name: "Rầy Phấn Trắng / Rầy Lưng Trắng",
    nameEn: "Whitebacked Planthopper",
    emoji: "🪲",
    severity: "high",
    symptoms: "Tương tự như rầy nâu, chúng chích hút nhựa cây làm lúa vàng úa, còi cọc. Nguy hiểm nhất, rầy lưng trắng là môi giới duy nhất truyền virus Lùn sọc đen phương Nam.",
    cause: "Côn trùng (Sogatella furcifera). Xuất hiện nhiều từ giai đoạn lúa đẻ nhánh đến làm đòng.",
    treatment: [
      "Vệ sinh đồng ruộng, dọn sạch cỏ dại (nhất là cỏ lồng vực) vì đây là ký chủ phụ.",
      "Gieo sạ thưa, bón phân cân đối.",
      "Sử dụng các loại thuốc đặc trị rầy khi mật độ vượt ngưỡng, phun tập trung vào gốc lúa."
    ]
  },
  {
    id: "southern_black_streaked_dwarf",
    name: "Bệnh Lùn Sọc Đen Phương Nam",
    nameEn: "Southern Rice Black-Streaked Dwarf Virus (SRBSDV)",
    emoji: "📉",
    severity: "high",
    symptoms: "Lúa thấp lùn, lá xanh đậm hơn bình thường, mép lá bị rách hình chữ V, có các u sáp sần sùi (sọc đen/trắng) dọc gân lá. Lúa không trổ bông được hoặc trổ nghẹn, hạt lép đen.",
    cause: "Do virus SRBSDV lây truyền qua trung gian là rầy lưng trắng. Bệnh KHÔNG lây qua hạt giống hay đất.",
    treatment: [
      "KHÔNG CÓ THUỐC ĐẶC TRỊ VIRUS. Biện pháp duy nhất là PHÒNG BỆNH.",
      "Nhổ bỏ và tiêu hủy (đốt/chôn sâu) ngay những cây lúa bị bệnh từ sớm để diệt nguồn lây.",
      "Phun thuốc diệt rầy lưng trắng (môi giới truyền bệnh) trên diện rộng nếu phát hiện bệnh."
    ]
  },
  {
    id: "weeds",
    name: "Cỏ Dại",
    nameEn: "Weeds",
    emoji: "🌿",
    severity: "medium",
    symptoms: "Cỏ lồng vực, cỏ đuôi phụng, cỏ chác lác... mọc xen lẫn với lúa, cạnh tranh trực tiếp dinh dưỡng, ánh sáng và nước làm lúa sinh trưởng kém, giảm năng suất.",
    cause: "Hạt cỏ có sẵn trong đất, lây lan qua nguồn nước hoặc do làm đất không kỹ trước khi gieo sạ.",
    treatment: [
      "Làm đất kỹ, cày ải phơi ruộng để tiêu diệt mầm cỏ.",
      "Quản lý nước tốt: giữ mực nước ruộng 3-5cm để ém cỏ, ngăn cỏ nảy mầm.",
      "Nhổ cỏ bằng tay, hoặc dùng thuốc trừ cỏ tiền nảy mầm/hậu nảy mầm (ưu tiên loại phân hủy nhanh để tránh ô nhiễm đất)."
    ]
  },
  {
    id: "golden_apple_snail",
    name: "Ốc Bươu Vàng",
    nameEn: "Golden Apple Snail",
    emoji: "🐌",
    severity: "high",
    symptoms: "Ốc cắn đứt mạ non hoặc gốc lúa mới cấy, làm khuyết dảnh lúa, mất mật độ trên ruộng. Thường thấy các ổ trứng màu hồng rực rỡ bám trên thân cây, bờ cỏ.",
    cause: "Sinh vật ngoại lai xâm hại (Pomacea canaliculata). Lây lan nhanh theo nguồn nước, sinh sản rất mạnh.",
    treatment: [
      "Bắt ốc thủ công, thu gom ổ trứng trên bờ mương và thân cây cỏ tiêu hủy.",
      "Thả vịt vào ruộng lúa (khi lúa đã cứng cây) để vịt ăn ốc non.",
      "Sử dụng bả mồi sinh học, hoặc rải thuốc diệt ốc có hoạt chất Niclosamide ở các vũng nước đọng nếu mật độ ốc quá cao."
    ]
  }
];

function DiseaseLibrary() {
  const [selectedDisease, setSelectedDisease] = useState(null);

  const getSeverityLabel = (severity) => {
    switch(severity) {
      case 'high': return <span className="disease-severity severity-high">Nguy hiểm cao</span>;
      case 'medium': return <span className="disease-severity severity-medium">Mức độ vừa</span>;
      case 'low': return <span className="disease-severity severity-low">Ít nguy hiểm</span>;
      default: return null;
    }
  };

  return (
    <div className="glass-panel" style={{ maxWidth: '1000px', margin: '0 auto', width: '100%' }}>
      <h2 style={{ textAlign: 'center', marginBottom: '8px', fontSize: '2.2rem', color: 'var(--primary-dark)' }}>Thư Viện Bệnh Cây Lúa</h2>
      <p style={{ textAlign: 'center', color: 'var(--text-muted)', marginBottom: '32px', fontSize: '1.05rem' }}>
        Tra cứu thông tin chi tiết các loại bệnh phổ biến nhất trên cây lúa
      </p>

      <div className="disease-grid">
        {DISEASES.map((disease) => (
          <div 
            key={disease.id} 
            className="disease-card"
            onClick={() => setSelectedDisease(disease)}
          >
            <div className="disease-card-header">
              <div className="disease-emoji">{disease.emoji}</div>
              <div>
                <div className="disease-card-title" style={{ color: 'var(--primary-dark)' }}>{disease.name}</div>
                <div className="disease-card-subtitle">{disease.nameEn}</div>
              </div>
            </div>
            <div className="disease-card-body">
              <p style={{ display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden', color: 'var(--text-main)' }}>
                {disease.symptoms}
              </p>
              {getSeverityLabel(disease.severity)}
            </div>
          </div>
        ))}
      </div>

      {selectedDisease && (
        <div className="modal-overlay" onClick={() => setSelectedDisease(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setSelectedDisease(null)}>×</button>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '24px' }}>
              <div className="disease-emoji" style={{ width: '64px', height: '64px', fontSize: '2.5rem', background: 'var(--bg-main)' }}>
                {selectedDisease.emoji}
              </div>
              <div>
                <h3 style={{ color: 'var(--primary-dark)' }}>{selectedDisease.name}</h3>
                <div style={{ color: 'var(--text-muted)', fontWeight: '500' }}>{selectedDisease.nameEn}</div>
                {getSeverityLabel(selectedDisease.severity)}
              </div>
            </div>

            <div className="modal-section">
              <h4>🔍 Triệu chứng nhận biết</h4>
              <p style={{ color: 'var(--text-main)' }}>{selectedDisease.symptoms}</p>
            </div>

            <div className="modal-section">
              <h4>🦠 Nguyên nhân gây bệnh & Điều kiện</h4>
              <p style={{ color: 'var(--text-main)' }}>{selectedDisease.cause}</p>
            </div>

            <div className="modal-section">
              <h4>🛡️ Biện pháp phòng & trị bệnh</h4>
              <ul style={{ paddingLeft: '24px', display: 'flex', flexDirection: 'column', gap: '8px', color: 'var(--text-main)' }}>
                {selectedDisease.treatment.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default DiseaseLibrary;
