from datetime import datetime
import shared.scraper as scraper
import scrapy


class SourcewellScraper(scraper.DefaultScraper):
    name = 'sourcewell'

    amendments_files = ['extension', 'modification', 'renewal']
    bid_solicitation_files = ['request for proposal', 'rfp', 'solicitation', 'bid doc', 'request for quote', 'rfq',
                              'rfb', 'request for bid', 'bid solicitation']
    bid_tabulation_files = ['bid tabulation', 'bid tab', 'evaluation']
    contract = ['contract']
    SITE_BASE_URL = 'https://www.sourcewell-mn.gov'


    def start_requests(self):
        """
        This function is implemented for you. It kicks off a request to the main Sourcewell
        contracts page and establishes a callback of self.parse_urls. The result of loading
        the main Sourcewell page will be in the response parameter of the callback function.
        """
        BASE_URL = 'https://www.sourcewell-mn.gov/contract-search?category=All&keyword='
        yield scrapy.Request(url=BASE_URL, callback=self.parse_urls)

    def parse_urls(self, response):
        contract_urls = response.css('div a.component__search-vendors-contracts-title::attr(href)').getall()

        for i in contract_urls:
            yield scrapy.Request(f'{self.SITE_BASE_URL}{i}', callback=self.parse_individual_page)

        next_page = response.css('a[rel="next"]::attr(href)').get()
        if next_page is not None:
            yield response.follow(next_page, callback=self.parse_urls)

        """
        You should implement this function for part one of the coding exercise.
        This function should take in the response from start_requests and output 
        all of the URLs for contracts that need to be parsed. You can read more about
        Scrapy response objects here: 
        https://docs.scrapy.org/en/latest/topics/request-response.html#response-objects

        You can access the results of loading the main Sourcewell webpage referenced in start_requests
        by using Scrapy selectors. You can read more about Scrapy selectors here: 
        https://docs.scrapy.org/en/latest/topics/selectors.html.

        You can add extra helper functions/steps if you would like to, but please make sure that
        your final step yields contract URLs with a callback funciton of parse_individual_page.

        A contract URL should look something like this: 
        https://www.sourcewell-mn.gov/cooperative-purchasing/020817-acr
        The last portion of the URL will vary for different contracts.

        You should yield a scrapy.Request object for each URL that will need to be parsed. The
        callback should be set as parse_individual_page, which you will implement later (for now
        it just prints out what you've yielded).

        Code example:
        yield scrapy.Request(url=<Your URL>, callback=self.parse_individual_page)
        """
        pass

    def parse_individual_page(self, response):

        item = {
            'buyer_lead_agency': 'Sourcewell',
            'cooperative_language': True,
            'buyer_lead_agency_state': 'MN',
            'cooperative_affiliation': 'Sourcewell',
            'contract_type': 'COMPETITIVELY_BID_CONTRACT',
            'service_area_national': True,
            'source_url': response.url,
        }
        """  
        You will implement this function for part two of the coding exercise.
        Please do not modify it until you start part two.

        For part two you should yield one dictionary for each contract page that you
        visited. Note that in the example output many fields are nested under a "fields"
        tag. The base scraper takes care of this automatically and you do not need to
        do that here.
        """
        files = self.get_supplierinfo(response)
        if files:
            item['suppliers'] = files

        files = self.get_contract_title(response)
        if files:
            item['title'] = files

        files = self.get_contractnumber(response)
        if files:
            item['contract_number'] = files

        files = self.get_expiration(response)
        if files:
            item['expiration'] = files

        files = self.get_summary(response)
        if files:
            item['summary'] = files

        files = self.get_effective_date(response)
        if files:
            item['effective'] = files

        files = self.get_files(response, file_keys=self.contract)
        if files:
            item['contract_files'] = files

        files = self.get_files(response, file_keys=self.amendments_files)
        if files:
            item['amendments_files'] = files

        files = self.get_files(response, file_keys=self.bid_solicitation_files)
        if files:
            item['bid_solicitation_files'] = files

        files = self.get_files(response, file_keys=self.bid_tabulation_files)
        if files:
            item['bid_tabulation_files'] = files

        files = self.get_other_files(response)
        if files:
            item['other_docs_files'] = files

        files = self.price_section_files(response)
        if files:
            item['pricing_files'] = files

        files = self.suppliers_data(response)
        if files:
            item['supplier_contacts'] = files

        files = self.buyers_data(response)
        if files:
            item['buyer_contacts'] = files

        yield item

    def get_supplierinfo(self, response):
        return response.css('.vendor-contract-header__content h1::text').get()

    def get_contract_title(self, response):
        return response.css('.vendor-contract-header__content p.lead::text').get()

    def get_contractnumber(self, response):
        number = response.css('.vendor-contract-header__content p::text').re(r'(#.+)')
        return number and number[0]

    def get_expiration(self, response):
        expiration_maturity = response.css('.vendor-contract-header__content p::text').re(r'Maturity Date:(.+)')[0].strip()
        other_expiration = response.css('#tab-contract-documents div::text').re(r'Effective.+-(.+)')[0].strip()

        expiration_date = datetime.strptime(expiration_maturity, '%m/%d/%Y')
        other_expiration_date = datetime.strptime(other_expiration, '%m/%d/%Y')
        if other_expiration_date > expiration_date:
            return other_expiration

        return expiration_maturity

        # it is getting the summary lists from the products and services section
    def get_summary(self, response):
        summary = response.css('.field--name-field-ps-summary li::text').getall()
        return summary and ', '.join(summary)

    def get_effective_date(self, response):
        effective_date = response.css('#tab-contract-documents div::text').re(r'Effective(.+)-')
        return effective_date and effective_date[0].strip()
        # it is returning the both dates scraped from the date div on the contract documents.

    def get_files(self, response, file_keys):
        files_selector = response.css('.file-icon + .file-link a')
        files = []
        for file_selector in files_selector:
            file_name = file_selector.css('::text').get()
            if any([file_key in file_name.lower() for file_key in file_keys]):
                files.append({
                    'name': file_name,
                    'url': file_selector.css('::attr(href)').get(),
                })

                return files

    def get_other_files(self, response):
        files_selector = response.css('.file-icon + .file-link a')
        file_keys = self.amendments_files + self.bid_tabulation_files + self.contract + self.bid_solicitation_files
        files = []
        for file_selector in files_selector:
            file_name = file_selector.css('::text').get()
            if all([file_key not in file_name.lower() for file_key in file_keys]):
                files.append({
                    'name': file_name,
                    'url': file_selector.css('::attr(href)').get(),
                })

        return files

    def price_section_files(self, response):
        files_scrapped = []
        for i in response.css('#tab-pricing a'):
            files_scrapped.append({
                'name': i.css('::text').get(),
                'url': f'{self.SITE_BASE_URL}{i.css("::attr(href)").get()}',
            })

        return files_scrapped

    def buyers_data(self, response):
        data = {}
        temp = response.css('.field--name-field-sourcewell-contact-info + article strong::text').get()
        if temp:
            data["name"] = temp

        temp = response.css('.field--name-field-sourcewell-contact-info + article .field--label-inline .field--item::text').get()
        if temp:
            data["phone"] = temp

        temp = response.css('.field--name-field-sourcewell-contact-info + article .field--label-inline .field--item a::text').get()
        if temp:
            data["email"] = temp

        return [data]

    def suppliers_data(self, response):
        data = {}
        temp = response.css('.field--name-field-vendor-contact-info + article strong::text').get()
        if temp:
            data["name"] = temp

        temp = response.css('.field--name-field-vendor-contact-info + article .field--label-inline .field--item::text').get()
        if temp:
            data["phone"] = temp

        temp = response.css('.field--name-field-vendor-contact-info + article .field--label-inline .field--item a::text').get()
        if temp:
            data["email"] = temp

        return [data]


def handler(*args, **kwargs):
    scraper.run_scraper(SourcewellScraper)


if __name__ == "__main__":
    handler()
