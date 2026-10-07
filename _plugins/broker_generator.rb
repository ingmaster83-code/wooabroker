require 'json'

module Jekyll
  class BrokerPageGenerator < Generator
    safe true
    priority :normal

    DONG_CAP = 300       # 동/도로 허브 페이지당 서버사이드 렌더링 상한
    ROAD_MIN = 3         # 도로 허브를 만드는 최소 사무소 수
    NEAR_COUNT = 6       # 상세 페이지의 같은 동 사무소 링크 수

    def generate(site)
      shard_files = Dir.glob(File.join(site.source, '_rawdata', 'broker_*.json'))
                       .reject { |f| File.basename(f) == 'broker_raw.json' }

      n_office = n_sg = n_dong = n_road = 0

      shard_files.sort.each do |path|
        do_short = File.basename(path, '.json').sub('broker_', '')
        items = load_json(path)
        next if items.empty?

        by_sg = items.group_by { |i| i['sigungu'] }
        site.pages << DoPage.new(site, do_short, items.size, by_sg)

        by_sg.each do |sg, sg_items|
          sg_slug = sg_items.first['sgSlug']
          by_dong = sg_items.group_by { |i| i['dong'] }
          by_road = sg_items.select { |i| !i['roadName'].to_s.empty? }.group_by { |i| i['roadName'] }
                            .select { |_, v| v.size >= ROAD_MIN }

          site.pages << SigunguPage.new(site, do_short, sg, sg_slug, sg_items.size, by_dong, by_road)
          n_sg += 1

          by_dong.each do |dong, list|
            site.pages << DongPage.new(site, do_short, sg, sg_slug, dong, list)
            n_dong += 1

            # 같은 동 사무소를 순환 배열로 이웃 연결 (모든 페이지가 서로 다른 이웃을 링크)
            sorted = list.sort_by { |i| [i['regDate'].to_s, i['regNo']] }
            sorted.each_with_index do |o, idx|
              nb = (1..[NEAR_COUNT, sorted.size - 1].min).map { |k| sorted[(idx + k) % sorted.size] }
                   .map { |x| { 'slug' => x['slug'], 'name' => x['officeName'], 'kind' => x['kind'] } }
              site.pages << OfficePage.new(site, o, nb)
              n_office += 1
            end
          end

          by_road.each do |road, list|
            site.pages << RoadPage.new(site, do_short, sg, sg_slug, road, list)
            n_road += 1
          end
        end
      end

      Jekyll.logger.info 'BrokerGenerator:', "시군구 #{n_sg} / 동 #{n_dong} / 도로 #{n_road} / 사무소 #{n_office}"
    end

    private

    def load_json(path)
      JSON.parse(File.read(path, encoding: 'utf-8'))
    rescue => e
      Jekyll.logger.warn 'BrokerGenerator:', "#{path} 로드 실패: #{e.message}"
      []
    end
  end

  class DoPage < Page
    def initialize(site, do_short, total, by_sg)
      @site = site; @base = site.source; @dir = "region/#{do_short}"; @name = 'index.html'
      list = by_sg.map { |sg, l| { 'name' => sg, 'slug' => l.first['sgSlug'], 'count' => l.size } }.sort_by { |h| -h['count'] }
      process(@name)
      read_yaml(File.join(@base, '_layouts'), 'do.html')
      data['layout'] = 'do'
      data['doShort'] = do_short
      data['totalCount'] = total
      data['sigunguList'] = list
      data['title'] = "#{do_short} 공인중개사사무소 #{total}곳 - 시군구별 등록 정보"
      data['description'] = "#{do_short}의 공인중개사사무소 #{total}곳을 시군구·동별로 확인하세요. 개설등록번호·등록일·대표자·공제가입 여부를 공공데이터로 안내합니다."[0, 155]
    end
  end

  class SigunguPage < Page
    def initialize(site, do_short, sg, sg_slug, total, by_dong, by_road)
      @site = site; @base = site.source; @dir = "region/#{do_short}/#{sg_slug}"; @name = 'index.html'
      dongs = by_dong.map { |dg, l| { 'name' => dg, 'count' => l.size } }
                     .sort_by { |h| h['name'] == '기타' ? [1, 0] : [0, -h['count']] }
      roads = by_road.map { |r, l| { 'name' => r, 'count' => l.size } }.sort_by { |h| -h['count'] }.first(40)
      process(@name)
      read_yaml(File.join(@base, '_layouts'), 'sigungu.html')
      data['layout'] = 'sigungu'
      data['doShort'] = do_short
      data['sigungu'] = sg
      data['sgSlug'] = sg_slug
      data['totalCount'] = total
      data['dongList'] = dongs
      data['roadList'] = roads
      data['title'] = "#{do_short} #{sg} 공인중개사사무소 #{total}곳 - 동별 부동산 등록 정보"
      data['description'] = "#{do_short} #{sg}의 공인중개사사무소 #{total}곳을 동·읍·면과 도로별로 찾아보세요. 개설등록번호와 공제가입 여부를 확인할 수 있습니다."[0, 155]
    end
  end

  class DongPage < Page
    def initialize(site, do_short, sg, sg_slug, dong, list)
      @site = site; @base = site.source; @dir = "region/#{do_short}/#{sg_slug}/#{dong}"; @name = 'index.html'
      capped = list.sort_by { |i| i['officeName'] }.first(BrokerPageGenerator::DONG_CAP)
      label = dong == '기타' ? '기타 지역' : dong
      process(@name)
      read_yaml(File.join(@base, '_layouts'), 'dong.html')
      data['layout'] = 'dong'
      data['doShort'] = do_short
      data['sigungu'] = sg
      data['sgSlug'] = sg_slug
      data['dong'] = dong
      data['dongLabel'] = label
      data['totalCount'] = list.size
      data['truncated'] = list.size > BrokerPageGenerator::DONG_CAP
      data['items'] = capped
      data['title'] = "#{sg} #{label} 공인중개사사무소·부동산 #{list.size}곳 (#{do_short})"
      data['description'] = "#{do_short} #{sg} #{label}의 공인중개사사무소 #{list.size}곳 목록. 상호·개설등록번호·주소·공제가입 여부를 확인하고 계약 전 등록 여부를 점검하세요."[0, 155]
    end
  end

  class RoadPage < Page
    def initialize(site, do_short, sg, sg_slug, road, list)
      @site = site; @base = site.source; @dir = "road/#{do_short}/#{sg_slug}/#{road}"; @name = 'index.html'
      capped = list.sort_by { |i| i['officeName'] }.first(BrokerPageGenerator::DONG_CAP)
      process(@name)
      read_yaml(File.join(@base, '_layouts'), 'road.html')
      data['layout'] = 'road'
      data['doShort'] = do_short
      data['sigungu'] = sg
      data['sgSlug'] = sg_slug
      data['road'] = road
      data['totalCount'] = list.size
      data['truncated'] = list.size > BrokerPageGenerator::DONG_CAP
      data['items'] = capped
      data['title'] = "#{sg} #{road} 공인중개사사무소·부동산 #{list.size}곳"
      data['description'] = "#{do_short} #{sg} #{road}에 있는 공인중개사사무소 #{list.size}곳의 상호·개설등록번호·주소를 확인하세요."[0, 155]
    end
  end

  class OfficePage < Page
    def initialize(site, o, near)
      @site = site; @base = site.source; @dir = "office/#{o['slug']}"; @name = 'index.html'
      process(@name)
      read_yaml(File.join(@base, '_layouts'), 'office.html')
      data.merge!(o)
      data['layout'] = 'office'
      data['near'] = near
      dong_label = o['dong'] == '기타' ? '' : " #{o['dong']}"
      data['dongLabel'] = o['dong'] == '기타' ? '기타 지역' : o['dong']
      year = o['regDate'].to_s[0, 4].to_i
      data['regYears'] = year > 1990 ? (2026 - year) : nil
      data['title'] = "#{o['officeName']} (#{o['doShort']} #{o['sigungu']}#{dong_label}) 개설등록번호 #{o['regNo']}"
      data['description'] = "#{o['doShort']} #{o['sigungu']}#{dong_label} #{o['officeName']}의 개설등록번호(#{o['regNo']}), 개설등록일, 공제가입 여부, 주소 정보를 확인하세요."[0, 155]
    end
  end

  # 사이트맵: 80k URL이라 jekyll-sitemap(단일 파일, 5만 건 한도 초과) 대신 40,000건씩 분할 + 인덱스
  class BrokerSitemapGenerator < Generator
    safe true
    priority :lowest
    CHUNK = 40_000

    def generate(site)
      urls = site.pages.reject { |p| p.url.to_s.end_with?('.json', '.xml', '.txt', '.js', '.css') || p.url.to_s == '/404.html' || p.data['sitemap'] == false }
                       .map { |p| p.url }.uniq
      base = site.config['url'].to_s
      chunks = urls.each_slice(CHUNK).to_a
      chunks.each_with_index do |c, idx|
        body = +"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n"
        c.each { |u| body << "  <url><loc>#{base}#{u}</loc></url>\n" }
        body << "</urlset>\n"
        site.pages << raw_page(site, "sitemap-#{idx + 1}.xml", body)
      end
      index = +"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<sitemapindex xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n"
      chunks.each_index { |idx| index << "  <sitemap><loc>#{base}/sitemap-#{idx + 1}.xml</loc></sitemap>\n" }
      index << "</sitemapindex>\n"
      site.pages << raw_page(site, 'sitemap.xml', index)
      Jekyll.logger.info 'BrokerSitemap:', "#{urls.size}개 URL → #{chunks.size}개 사이트맵"
    end

    private

    def raw_page(site, name, content)
      pg = PageWithoutAFile.new(site, site.source, '', name)
      pg.content = content
      pg.data['layout'] = nil
      pg.data['sitemap'] = false
      pg
    end
  end
end
